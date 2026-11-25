
from datetime import datetime
from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db, settings
from app.models import AuthUser, HiddenConversation, UserSettings

router = APIRouter(
    prefix="/api/v1/chats",
    tags=["Chats"],
)

CHATBOT_API_URL = (settings.CHATBOT_API_URL or "").rstrip("/")

# Backs up the hidden_conversations table, in case saving a conversation's ID fails.
HIDDEN_CONVERSATION_TITLE = "__medirounds_suggestions__"


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20000)


class RenameChatRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


def require_chatbot_url() -> str:
    if not CHATBOT_API_URL:
        raise HTTPException(
            status_code=503,
            detail="CHATBOT_API_URL is not configured",
        )
    return CHATBOT_API_URL


def rag_headers(user_id: str, accept: str) -> dict[str, str]:
    headers = {
        "X-User-ID": user_id,
        "Accept": accept,
    }

    api_key = settings.CHATBOT_API_KEY
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    return headers


def check_rag_status(response: httpx.Response) -> None:
    if response.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail="RAG resource not found",
        )

    if response.is_error:
        raise HTTPException(
            status_code=502,
            detail=(
                "RAG service returned HTTP "
                f"{response.status_code}"
            ),
        )


async def rag_request(
    method: str,
    path: str,
    user_id: str,
    payload: dict | None = None,
) -> Any:
    base_url = require_chatbot_url()

    try:
        async with httpx.AsyncClient(
            timeout=120.0,
        ) as client:
            response = await client.request(
                method,
                f"{base_url}{path}",
                headers=rag_headers(user_id, "application/json"),
                json=payload,
            )

            check_rag_status(response)

            # Successful deletes have no body.
            if response.status_code == 204:
                return None

            return response.json()

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail="Unable to reach RAG service",
        ) from exc


def map_message(record: dict) -> dict:
    role = record["role"]

    if role not in ("user", "assistant"):
        raise ValueError(f"Unsupported message role: {role}")

    return {
        "id": record["id"],
        "role": role,
        "content": record["content"],
        "createdAt": record["created_at"],
    }


def map_conversation(
    record: dict,
    messages: list[dict] | None = None,
) -> dict:
    return {
        "id": record["id"],
        "title": record["title"],
        "createdAt": record["created_at"],
        "updatedAt": record["updated_at"],
        "messages": messages or [],
    }


async def list_rag_conversations(
    user_id: str,
    db: AsyncSession,
) -> list[dict]:
    """List the user's conversations, leaving out hidden ones."""
    data = await rag_request(
        "GET",
        "/conversations",
        user_id,
    )

    if not isinstance(data, list):
        raise HTTPException(
            status_code=502,
            detail="Unexpected RAG conversations response",
        )

    # Queried after the RAG call, so a conversation hidden in the meantime is left out too.
    hidden_ids = set(
        await db.scalars(
            select(HiddenConversation.conversation_id).where(
                HiddenConversation.user_id == user_id,
            )
        )
    )

    return [
        conversation
        for conversation in data
        if conversation["id"] not in hidden_ids
        and conversation["title"] != HIDDEN_CONVERSATION_TITLE
    ]


async def list_rag_messages(
    conversation_id: str,
    user_id: str,
) -> list[dict]:
    data = await rag_request(
        "GET",
        f"/conversations/{conversation_id}/messages",
        user_id,
    )

    if not isinstance(data, list):
        raise HTTPException(
            status_code=502,
            detail="Unexpected RAG messages response",
        )

    return sorted(
        [
            map_message(message)
            for message in data
            if message.get("role") in ("user", "assistant")
        ],
        key=lambda message: message["createdAt"],
    )


async def rag_chat(
    conversation_id: str,
    user_id: str,
    content: str,
) -> dict:
    """Send a message and return the completed reply once it has been saved."""
    base_url = require_chatbot_url()
    messages_path = f"/conversations/{conversation_id}/messages"

    seen_ids = {
        message["id"]
        for message in await rag_request("GET", messages_path, user_id)
    }

    # /chat always answers with an event stream. Read it to the end, then fetch the saved reply.
    try:
        async with httpx.AsyncClient(
            timeout=120.0,
        ) as client:
            async with client.stream(
                "POST",
                f"{base_url}/chat",
                headers=rag_headers(user_id, "text/event-stream"),
                json={
                    "conversation_id": conversation_id,
                    "message": content,
                },
            ) as response:
                check_rag_status(response)

                async for _ in response.aiter_bytes():
                    pass

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail="Unable to reach RAG service",
        ) from exc

    # A failed answer also streams with HTTP 200, so only accept a new, completed reply.
    replies = [
        message
        for message in await rag_request("GET", messages_path, user_id)
        if message["role"] == "assistant"
        and message["status"] == "completed"
        and message["id"] not in seen_ids
    ]

    if not replies:
        raise HTTPException(
            status_code=502,
            detail="RAG service did not complete its answer",
        )

    return map_message(
        max(replies, key=lambda message: message["created_at"])
    )


@router.get("")
async def list_chats(
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = str(user.id)

    conversations = await list_rag_conversations(user_id, db)

    chats = []

    for conversation in conversations:
        messages = await list_rag_messages(
            conversation["id"],
            user_id,
        )

        chats.append(
            map_conversation(conversation, messages)
        )

    return sorted(
        chats,
        key=lambda chat: chat["updatedAt"],
        reverse=True,
    )


@router.post("")
async def create_chat(
    user: AuthUser = Depends(get_current_user),
):
    user_id = str(user.id)

    conversation = await rag_request(
        "POST",
        "/conversations",
        user_id,
        payload={
            "title": "New conversation",
            "domain": "medical",
        },
    )

    return map_conversation(conversation)


@router.get("/{conversation_id}")
async def get_chat(
    conversation_id: UUID,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = str(user.id)
    chat_id = str(conversation_id)

    conversations = await list_rag_conversations(user_id, db)

    conversation = next(
        (
            item
            for item in conversations
            if item["id"] == chat_id
        ),
        None,
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    messages = await list_rag_messages(
        chat_id,
        user_id,
    )

    return map_conversation(conversation, messages)

EXPERIENCE_PROMPTS = {
    "student": (
        "The user is a medical student. Explain concepts from the ground up. "
        "Define medical terminology and abbreviations on first use. "
        "Include relevant pathophysiology to build understanding. "
        "Use a structured, teaching-oriented tone."
    ),
    "resident": (
        "The user is a medical resident. Provide evidence-based clinical reasoning "
        "with references to current guidelines (ADA, EASD, KDIGO). "
        "Highlight key decision points and common pitfalls. "
        "Assume foundational medical knowledge."
    ),
    "fellow": (
        "The user is a subspecialty fellow. Focus on nuanced clinical decision-making, "
        "multimorbidity considerations, and subspecialty-specific management strategies. "
        "Compare guideline recommendations where they diverge. "
        "Assume strong general medical knowledge."
    ),
    "attending": (
        "The user is an attending physician. Be concise and direct. "
        "Prioritize recent guideline updates, landmark trial results, and practice-changing evidence. "
        "Skip foundational explanations unless specifically asked."
    ),
    "advanced": (
        "The user is an advanced clinician or researcher. Provide expert-level detail "
        "including study design, statistical methodology, effect sizes, and confidence intervals. "
        "Discuss limitations of the evidence and areas of active investigation. "
        "Reference primary literature where possible."
    ),
}

@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: UUID,
    body: SendMessageRequest,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = str(user.id)
    chat_id = str(conversation_id)

    conversations = await list_rag_conversations(user_id, db)

    if not any(
        item["id"] == chat_id
        for item in conversations
    ):
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    # Look up the user's experience level from the DB
    user_settings = await db.scalar(
        select(UserSettings).where(
            UserSettings.user_id == user_id,
        )
    )
    experience = user_settings.experience if user_settings else ""
    prefix = EXPERIENCE_PROMPTS.get(experience, "")
    content = f"{prefix}\n\n{body.content}" if prefix else body.content

    return await rag_chat(chat_id, user_id, content)
