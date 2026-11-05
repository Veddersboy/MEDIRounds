
import os
from datetime import datetime
from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.models import AuthUser

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


@router.get("")
async def list_chats(
    user: AuthUser = Depends(get_current_user),
):
    user_id = str(user.id)

    conversations = await list_rag_conversations(user_id)

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

    return map_conversation(conversation, messages)


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: UUID,
    body: SendMessageRequest,
    user: AuthUser = Depends(get_current_user),
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

    return assistant_messages[-1]
