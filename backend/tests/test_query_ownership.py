from datetime import datetime, timezone

import pytest_asyncio
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.models import (
    AuthUser,
    ChatSession,
    Message,
    Citation,
    UserSettings,
    Base,
)
from app.ownership import (
    get_owned_chat,
    get_owned_message,
    get_owned_citation,
    get_owned_settings,
)

@pytest_asyncio.fixture
async def ownership_db(tmp_path):
    db_path = tmp_path / "ownership.db"

    sync_engine = create_engine(
        f"sqlite:///{db_path.as_posix()}"
    )

    Base.metadata.create_all(sync_engine)

    now = datetime.now(timezone.utc)

    with Session(sync_engine) as db:
        user_a = AuthUser(
            id="user-a",
            name="User A",
            email="a@example.com",
            email_verified=False,
        )

        user_b = AuthUser(
            id="user-b",
            name="User B",
            email="b@example.com",
            email_verified=False,
        )

        chat_a = ChatSession(
            id="chat-a",
            user_id="user-a",
            title="User A conversation",
            created_at=now,
            updated_at=now,
        )

        chat_b = ChatSession(
            id="chat-b",
            user_id="user-b",
            title="User B conversation",
            created_at=now,
            updated_at=now,
        )

        db.add_all([user_a, user_b, chat_a, chat_b])
        db.flush()

        message_a = Message(
            id="message-a",
            session_id="chat-a",
            role="user",
            content="User A message",
            created_at=now,
        )

        message_b = Message(
            id="message-b",
            session_id="chat-b",
            role="user",
            content="User B message",
            created_at=now,
        )

        db.add_all([message_a, message_b])
        db.flush()

        citation_a = Citation(
            id="citation-a",
            message_id="message-a",
            title="User A citation",
        )

        citation_b = Citation(
            id="citation-b",
            message_id="message-b",
            title="User B citation",
        )

        settings_a = UserSettings(user_id="user-a")
        settings_b = UserSettings(user_id="user-b")

        db.add_all([
            citation_a,
            citation_b,
            settings_a,
            settings_b,
        ])

        db.commit()

    sync_engine.dispose()

    async_engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path.as_posix()}",
        poolclass=NullPool,
    )

    sessionmaker = async_sessionmaker(
        async_engine,
        expire_on_commit=False,
    )

    async with sessionmaker() as session:
        yield session

    await async_engine.dispose()

@pytest.mark.asyncio
async def test_user_can_access_own_chat(ownership_db):
    chat = await get_owned_chat(
        "chat-a",
        "user-a",
        ownership_db,
    )

    assert chat.id == "chat-a"


@pytest.mark.asyncio
async def test_user_cannot_access_another_users_chat(ownership_db):
    with pytest.raises(HTTPException) as exc:
        await get_owned_chat(
            "chat-b",
            "user-a",
            ownership_db,
        )

    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_user_can_access_own_message(ownership_db):
    message = await get_owned_message(
        "message-a",
        "user-a",
        ownership_db,
    )

    assert message.id == "message-a"


@pytest.mark.asyncio
async def test_user_cannot_access_another_users_message(ownership_db):
    with pytest.raises(HTTPException) as exc:
        await get_owned_message(
            "message-b",
            "user-a",
            ownership_db,
        )

    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_user_can_access_own_citation(ownership_db):
    citation = await get_owned_citation(
        "citation-a",
        "user-a",
        ownership_db,
    )

    assert citation.id == "citation-a"


@pytest.mark.asyncio
async def test_user_cannot_access_another_users_citation(ownership_db):
    with pytest.raises(HTTPException) as exc:
        await get_owned_citation(
            "citation-b",
            "user-a",
            ownership_db,
        )

    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_user_can_access_own_settings(ownership_db):
    settings = await get_owned_settings(
        "user-a",
        ownership_db,
    )

    assert settings.user_id == "user-a"


@pytest.mark.asyncio
async def test_user_cannot_access_another_users_settings(ownership_db):
    with pytest.raises(HTTPException) as exc:
        await get_owned_settings(
            "user-c",
            ownership_db,
        )

    assert exc.value.status_code == 404