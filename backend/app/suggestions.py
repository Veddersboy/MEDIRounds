"""Generates and caches each user's research recommendations."""
import asyncio
import json
import logging
import random
import re
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import HiddenConversation, ResearchRecommendations, UserSettings, utcnow
from app.routers import chats

logger = logging.getLogger(__name__)

SUGGESTIONS_SHOWN = 3
MAX_AGE = timedelta(hours=24)
# A refresh that failed or crashed can be retried after this long. Must exceed REFRESH_TIMEOUT_SECONDS.
REFRESH_CLAIM = timedelta(minutes=5)
REFRESH_TIMEOUT_SECONDS = 240
# Start a new hidden conversation after this many replies, in case the RAG service sends the whole history to the model.
MAX_REPLIES_PER_CONVERSATION = 10

TOPICS_PER_REFRESH = 4
QUESTIONS_PER_TOPIC = 3
MAX_QUESTIONS = TOPICS_PER_REFRESH * QUESTIONS_PER_TOPIC
MAX_QUESTION_LENGTH = 120

TOPICS = [
    "metformin and first-line therapy",
    "GLP-1 receptor agonists",
    "SGLT2 inhibitors",
    "insulin initiation and titration",
    "HbA1c interpretation and glycemic targets",
    "continuous glucose monitoring",
    "hypoglycemia",
    "chronic kidney disease",
    "heart failure",
    "atherosclerotic cardiovascular disease",
    "obesity and weight management",
    "hypertension and lipid management",
    "neuropathy and foot care",
    "retinopathy",
    "older adults",
    "lifestyle and nutrition",
]

AUDIENCES = {
    "student": "a medical student",
    "resident": "a medical resident",
    "fellow": "a subspecialty fellow",
    "attending": "an attending physician",
    "advanced": "an advanced clinician or researcher",
}


async def load_suggestions(user_id: str, db: AsyncSession) -> tuple[list[str], bool]:
    """Return up to three random cached questions, and whether the caller must start a refresh."""
    row = await db.get(ResearchRecommendations, user_id)
    questions = list(row.questions) if row else []

    if row is None:
        db.add(ResearchRecommendations(user_id=user_id))
        try:
            await db.commit()
        except IntegrityError:
            # Another request created the row first.
            await db.rollback()

    # A single UPDATE, so only one of several concurrent requests can claim the refresh.
    now = utcnow()
    claim = await db.execute(
        update(ResearchRecommendations)
        .where(
            ResearchRecommendations.user_id == user_id,
            or_(
                ResearchRecommendations.generated_at.is_(None),
                ResearchRecommendations.generated_at < now - MAX_AGE,
            ),
            or_(
                ResearchRecommendations.refresh_started_at.is_(None),
                ResearchRecommendations.refresh_started_at < now - REFRESH_CLAIM,
            ),
        )
        .values(refresh_started_at=now)
        .execution_options(synchronize_session=False)
    )
    # Keep this last: it returns the connection to the pool before the background refresh runs.
    await db.commit()

    selected = random.sample(questions, min(SUGGESTIONS_SHOWN, len(questions)))
    return selected, claim.rowcount == 1


async def refresh_suggestions(user_id: str) -> None:
    """Background task: generate new questions, replacing the cached ones only on success."""
    try:
        async with asyncio.timeout(REFRESH_TIMEOUT_SECONDS):
            questions = await generate_questions(user_id)
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(ResearchRecommendations)
                    .where(ResearchRecommendations.user_id == user_id)
                    .values(questions=questions, generated_at=utcnow(), refresh_started_at=None)
                )
                await db.commit()
    except Exception:
        # refresh_started_at stays set, so the next attempt waits until the claim expires.
        logger.warning("Refreshing research recommendations failed", exc_info=True)


async def generate_questions(user_id: str) -> list[str]:
    async with AsyncSessionLocal() as db:
        user_settings = await db.get(UserSettings, user_id)
    prompt = build_prompt(
        user_settings.experience if user_settings else "",
        user_settings.specialty if user_settings else "",
    )

    conversation_id = await open_hidden_conversation(user_id)
    reply = await chats.rag_chat(conversation_id, user_id, prompt)
    return parse_questions(reply["content"])


async def open_hidden_conversation(user_id: str) -> str:
    """Return the ID of the user's hidden conversation, creating one if needed."""
    async with AsyncSessionLocal() as db:
        conversation_id = await db.scalar(
            select(HiddenConversation.conversation_id)
            .where(HiddenConversation.user_id == user_id)
            .order_by(HiddenConversation.created_at.desc())
            .limit(1)
        )

    if conversation_id:
        try:
            messages = await chats.list_rag_messages(conversation_id, user_id)
        except HTTPException as exc:
            # Replace the conversation if it no longer exists on the RAG service.
            if exc.status_code != 404:
                raise
        else:
            replies = sum(message["role"] == "assistant" for message in messages)
            if replies < MAX_REPLIES_PER_CONVERSATION:
                return conversation_id

    conversation = await chats.rag_request(
        "POST",
        "/conversations",
        user_id,
        payload={"title": chats.HIDDEN_CONVERSATION_TITLE, "domain": "medical"},
    )
    # Record the ID before sending anything, so the conversation is already hidden.
    async with AsyncSessionLocal() as db:
        db.add(HiddenConversation(conversation_id=conversation["id"], user_id=user_id))
        await db.commit()
    return conversation["id"]


def build_prompt(experience: str, specialty: str) -> str:
    audience = AUDIENCES.get(experience, "a clinician")
    specialty = " ".join(specialty.split())
    if specialty:
        audience += f" specializing in {specialty}"
    topics = "; ".join(random.sample(TOPICS, TOPICS_PER_REFRESH))

    return (
        f"Suggest {MAX_QUESTIONS} research questions about type 2 diabetes for {audience}: "
        f"{QUESTIONS_PER_TOPIC} on each of these topics: {topics}. "
        "Only suggest questions that the available sources can answer. "
        "Each must make sense on its own, be a single sentence of at most 100 characters, "
        "and not describe a specific patient. "
        "Reply with only a JSON array of strings, without citations."
    )


def parse_questions(content: str) -> list[str]:
    """Extract the questions from a reply that may wrap the JSON array in other text."""
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\[", content):
        try:
            items, _ = decoder.raw_decode(content, match.start())
        except json.JSONDecodeError:
            continue

        questions: dict[str, str] = {}
        for item in items:
            if not isinstance(item, str):
                continue
            # Drop citation markers such as [1] or [2, 3].
            question = " ".join(re.sub(r"\[\d+(?:,\s*\d+)*\]", "", item).split())
            if question and len(question) <= MAX_QUESTION_LENGTH:
                questions.setdefault(question.casefold(), question)
        if len(questions) >= SUGGESTIONS_SHOWN:
            return list(questions.values())[:MAX_QUESTIONS]

    raise ValueError("RAG response did not contain enough usable questions")
