from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ChatSession,
    Message,
    Citation,
    UserSettings,
)

async def get_owned_chat(
    chat_id: str,
    user_id: str,
    db: AsyncSession,
) -> ChatSession:
    """
    Retrieve a chat only if it belongs to the specified user.
    """

    chat = await db.scalar(
        select(ChatSession).where(
            ChatSession.id == chat_id,
            ChatSession.user_id == user_id,
        )
    )

    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return chat

async def get_owned_message(
    message_id: str,
    user_id: str,
    db: AsyncSession,
) -> Message:
    """
    Retrieve a message only if it belongs to a chat owned by the user.
    """

    message = await db.scalar(
        select(Message)
        .join(ChatSession, Message.session_id == ChatSession.id)
        .where(
            Message.id == message_id,
            ChatSession.user_id == user_id,
        )
    )

    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    return message

async def get_owned_citation(
    citation_id: str,
    user_id: str,
    db: AsyncSession,
) -> Citation:
    """
    Retrieve a citation only if it belongs to a message
    in a chat owned by the user.
    """

    citation = await db.scalar(
        select(Citation)
        .join(Message, Citation.message_id == Message.id)
        .join(ChatSession, Message.session_id == ChatSession.id)
        .where(
            Citation.id == citation_id,
            ChatSession.user_id == user_id,
        )
    )

    if citation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Citation not found",
        )

    return citation

async def get_owned_settings(
    user_id: str,
    db: AsyncSession,
) -> UserSettings:
    """
    Retrieve settings belonging only to the specified user.
    """

    settings = await db.scalar(
        select(UserSettings).where(
            UserSettings.user_id == user_id,
        )
    )

    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User settings not found",
        )

    return settings
