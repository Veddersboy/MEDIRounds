
import os
import logging
import re
from datetime import datetime
from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import AuthUser, ChatSession

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/chats",
    tags=["Chats"],
)

CHATBOT_API_URL = os.getenv(
    "CHATBOT_API_URL", ""
).rstrip("/")


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


async def rag_request(
    method: str,
    path: str,
    user_id: str,
    payload: dict | None = None,
) -> Any:
    base_url = require_chatbot_url()

    headers = {
        "X-User-ID": user_id,
        "Accept": "application/json",
    }

    api_key = os.getenv("CHATBOT_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(
            timeout=120.0,
        ) as client:
            response = await client.request(
                method,
                f"{base_url}{path}",
                headers=headers,
                json=payload,
            )

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

            if not response.content:
                return None

            try:
                return response.json()
            except ValueError:
                if path == "/chat":
                    return response.text

                raise HTTPException(
                    status_code=502,
                    detail="Failed to parse RAG service JSON response",
                )

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
    title: str | None = None,
) -> dict:
    return {
        "id": record["id"],
        "title": title or record["title"],
        "createdAt": record["created_at"],
        "updatedAt": record["updated_at"],
        "messages": messages or [],
    }


async def list_rag_conversations(
    user_id: str,
) -> list[dict]:
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

    return data


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

# retrieves saved title
async def get_local_chat_title(
    chat_id: str,
    user_id: str,
    db: AsyncSession,
) -> str | None:
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == chat_id,
            ChatSession.user_id == user_id,
        )
    )

    session = result.scalar_one_or_none()

    return session.title if session else None

# creates or updates a chat title in local database
async def save_chat_title(
    chat_id: str,
    user_id: str,
    title: str,
    db: AsyncSession,
) -> None:
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == chat_id,
            ChatSession.user_id == user_id,
        )
    )

    session = result.scalar_one_or_none()

    if session:
        session.title = title
    else:
        session = ChatSession(
            id = chat_id,
            user_id = user_id,
            title = title,
        )
        db.add(session)

    await db.commit()

#
async def generate_chat_title(
    first_message: str,
    user_id: str,
) -> str | None:
    temp_id = None

    try:
        # generate temp chat
        conversation = await rag_request(
            "POST",
            "/conversations",
            user_id,
            payload={
                "title": "Temporary Title",
                "domain": "medical",
            },
        )

        temp_id = conversation["id"]

        # Title Generation Instructions
        prompt = (
            "Generate a concise, descriptive title based on the "
            "user's message below.\n"
            "Instructions:\n"
            "- Identify the main topic or question.\n"
            "- Make the title specific to the actual subject.\n"
            "- Do not assume the conversation is about Type 2 Diabetes.\n"
            "- Use clear, natural language.\n"
            "- Keep the title under 8 words.\n"
            "- Return only the title, without quotation marks, "
            "explanations, or additional text.\n\n"
            f"User's First message: {first_message}"
        )

        await rag_request(
            "POST",
            "/chat",
            user_id,
            payload={
                "conversation_id": temp_id,
                "message": prompt,
            },
        )

        messages = await list_rag_messages(
            temp_id,
            user_id,
        )

        assistant_messages = [
            message for message in messages
            if message["role"] == "assistant"
        ]

        if not assistant_messages:
            return None

        title = assistant_messages[-1]["content"].strip()
        title = title.strip("\' ")
        title = re.sub(r"\s+", " ", title)

        return title[:255] if title else None

    except Exception:
        logger.exception("Title generation failed")
        return None

    # delete temporary conversation
    finally:
        if temp_id:
            try:
                await rag_request(
                    "DELETE",
                    f"/conversations/{temp_id}",
                    user_id,
                )
            except Exception:
                logger.exception("Failed to delete temporary conversation")

@router.get("")
async def list_chats(
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = str(user.id)

    conversations = await list_rag_conversations(user_id)

    chats = []

    for conversation in conversations:
        messages = await list_rag_messages(
            conversation["id"],
            user_id,
        )

        local_title = await get_local_chat_title(
            conversation["id"],
            user_id,
            db,
        )

        chats.append(
            map_conversation(conversation, messages, local_title,)
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

    conversations = await list_rag_conversations(user_id)

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

    local_title = await get_local_chat_title(
        chat_id,
        user_id,
        db,
    )

    return map_conversation(conversation, messages, local_title,)


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: UUID,
    body: SendMessageRequest,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = str(user.id)
    chat_id = str(conversation_id)

    conversations = await list_rag_conversations(user_id)

    if not any(
        item["id"] == chat_id
        for item in conversations
    ):
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    # check to see if current message is user's first message
    messages_before = await list_rag_messages(chat_id,user_id,)

    is_first_message = not any(
        message["role"] == "user"
        for message in messages_before
    )

    result = await rag_request(
        "POST",
        "/chat",
        user_id,
        payload={
            "conversation_id": chat_id,
            "message": body.content,
        },
    )

    messages = await list_rag_messages(
        chat_id,
        user_id,
    )

    assistant_messages = [
        message
        for message in messages
        if message["role"] == "assistant"
    ]

    if not assistant_messages:
        raise HTTPException(
            status_code=502,
            detail="RAG response was not persisted",
        )

    if is_first_message:
        title = await generate_chat_title(
            body.content,
            user_id,
        )

        if title:
            try:
                await save_chat_title(chat_id, user_id, title, db)
            except Exception:
                await db.rollback()
                logger.exception("Failed to save chat title")

    return assistant_messages[-1]
