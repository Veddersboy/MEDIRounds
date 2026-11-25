import asyncio
import json
from datetime import datetime, timedelta, timezone
from functools import partial
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app import suggestions
from app.database import get_db, settings
from app.main import app
from app.models import AuthSession, AuthUser, Base, HiddenConversation, ResearchRecommendations, UserSettings
from app.routers import chats
from tests.test_auth import COOKIE, SECRET, sign

URL = "/api/v1/suggestions"
USER = "user-1"
OLD = ["Old A?", "Old B?", "Old C?", "Old D?"]
NEW = [f"New question {n}?" for n in range(12)]


class FakeRag:
    """In-memory stand-in for the RAG service, at the HTTP level."""

    def __init__(self):
        self.conversations = {}
        self.prompts = []
        self.reply = json.dumps(NEW)
        self.status = "completed"  # status the next reply is saved with; None saves nothing

    def add(self, title="Visible"):
        conversation_id = str(uuid4())
        self.conversations[conversation_id] = {
            "id": conversation_id,
            "title": title,
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
            "messages": [],
        }
        return conversation_id

    def add_message(self, conversation_id, role, content, status="completed"):
        messages = self.conversations[conversation_id]["messages"]
        messages.append({
            "id": str(uuid4()),
            "role": role,
            "content": content,
            "status": status,
            "created_at": f"{len(messages):04}",
        })

    def handle(self, request):
        assert request.headers["X-User-ID"] == USER
        path = request.url.path
        payload = json.loads(request.content) if request.content else None
        if path == "/conversations":
            if request.method == "GET":
                return httpx.Response(200, json=list(self.conversations.values()))
            return httpx.Response(201, json=self.conversations[self.add(payload["title"])])
        if path == "/chat":
            self.prompts.append(payload["message"])
            if self.status:
                self.add_message(payload["conversation_id"], "user", payload["message"])
                self.add_message(payload["conversation_id"], "assistant", self.reply, self.status)
            return httpx.Response(200, headers={"Content-Type": "text/event-stream"}, content=b"event: x\ndata: y\n\n")
        conversation = self.conversations.get(path.split("/")[2])
        if conversation is None:
            return httpx.Response(404)
        return httpx.Response(200, json=conversation["messages"])


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BETTER_AUTH_SECRET", SECRET)
    path = (tmp_path / "suggestions.db").as_posix()
    sync_engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(sync_engine)
    now = datetime.now(timezone.utc)
    with Session(sync_engine) as db:
        db.add(AuthUser(id=USER, name="Ada", email="ada@example.com", email_verified=False))
        db.add(AuthSession(id="s", token="token", user_id=USER, expires_at=now + timedelta(days=7), updated_at=now))
        db.commit()

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
    sessionmaker = async_sessionmaker(async_engine, expire_on_commit=False)

    async def test_db():
        async with sessionmaker() as session:
            yield session

    rag = FakeRag()
    monkeypatch.setattr(chats, "CHATBOT_API_URL", "http://rag.test")
    transport = httpx.MockTransport(rag.handle)
    monkeypatch.setattr(chats.httpx, "AsyncClient", partial(httpx.AsyncClient, transport=transport))
    monkeypatch.setattr(suggestions, "AsyncSessionLocal", sessionmaker)
    app.dependency_overrides[get_db] = test_db
    client = TestClient(app)
    client.cookies.set(COOKIE, sign("token"))
    with Session(sync_engine, expire_on_commit=False) as db:
        yield client, rag, db, sessionmaker
    app.dependency_overrides.clear()
    sync_engine.dispose()


def add_row(db, generated=None, started=None):
    now = datetime.now(timezone.utc)
    db.add(
        ResearchRecommendations(
            user_id=USER,
            questions=[] if generated is None else OLD,
            generated_at=None if generated is None else now - generated,
            refresh_started_at=None if started is None else now - started,
        )
    )
    db.commit()


def get_row(db):
    """Read the row as committed by the app, without leaving a read transaction open."""
    db.expire_all()
    row = db.get(ResearchRecommendations, USER)
    db.commit()
    return row


def hidden_ids(db):
    ids = list(db.scalars(select(HiddenConversation.conversation_id).order_by(HiddenConversation.created_at)))
    db.commit()
    return ids


def test_requires_sign_in(env):
    client, rag, _, _ = env
    client.cookies.clear()
    assert client.get(URL).status_code == 401
    assert rag.prompts == []


def test_first_request_is_empty_then_serves_generated_questions(env):
    client, rag, db, _ = env
    first = client.get(URL)
    assert (first.status_code, first.json()) == (200, [])

    second = client.get(URL).json()
    assert len(set(second)) == 3 and set(second) <= set(NEW)
    assert len(rag.prompts) == 1
    row = get_row(db)
    assert row.questions == NEW and row.generated_at and row.refresh_started_at is None
    assert hidden_ids(db) == list(rag.conversations)


def test_fresh_questions_are_not_refreshed(env):
    client, rag, db, _ = env
    add_row(db, generated=timedelta(hours=23))
    response = client.get(URL).json()
    assert len(response) == 3 and set(response) <= set(OLD)
    assert rag.prompts == []


def test_stale_questions_are_served_while_refreshing(env):
    client, _, db, _ = env
    add_row(db, generated=timedelta(hours=25))
    response = client.get(URL).json()
    assert len(response) == 3 and set(response) <= set(OLD)
    assert get_row(db).questions == NEW


def test_refresh_in_progress_is_not_repeated(env):
    client, rag, db, _ = env
    add_row(db, generated=timedelta(hours=25), started=timedelta(minutes=1))
    response = client.get(URL).json()
    assert len(response) == 3 and set(response) <= set(OLD)
    assert rag.prompts == []


def test_expired_claim_is_retried(env):
    client, rag, db, _ = env
    add_row(db, started=timedelta(minutes=6))
    client.get(URL)
    assert len(rag.prompts) == 1


@pytest.mark.parametrize("row_exists", [True, False])
def test_concurrent_requests_claim_one_refresh(env, row_exists):
    _, _, db, sessionmaker = env
    if row_exists:
        add_row(db, generated=timedelta(hours=25))

    async def load():
        async with sessionmaker() as session:
            return (await suggestions.load_suggestions(USER, session))[1]

    async def load_many():
        return await asyncio.gather(*(load() for _ in range(5)))

    assert asyncio.run(load_many()).count(True) == 1


def test_failed_refresh_keeps_questions_and_waits_to_retry(env):
    client, rag, db, _ = env
    rag.reply = "Sorry, I can't help with that."
    add_row(db, generated=timedelta(hours=25))
    assert client.get(URL).status_code == 200
    assert client.get(URL).status_code == 200
    assert len(rag.prompts) == 1
    row = get_row(db)
    assert row.questions == OLD and row.refresh_started_at


@pytest.mark.parametrize("status", [None, "pending", "failed"])
def test_incomplete_reply_is_not_used(env, status):
    client, rag, db, _ = env
    client.get(URL)
    row = get_row(db)
    row.questions, row.generated_at = OLD, datetime.now(timezone.utc) - timedelta(hours=25)
    db.commit()
    rag.status = status
    client.get(URL)
    assert len(rag.prompts) == 2
    assert get_row(db).questions == OLD


@pytest.mark.parametrize("replies,expected", [(9, 1), (10, 2)])
def test_conversation_is_reused_until_reply_limit(env, replies, expected):
    client, rag, db, _ = env
    conversation_id = rag.add(chats.HIDDEN_CONVERSATION_TITLE)
    for _ in range(replies):
        rag.add_message(conversation_id, "assistant", "[]")
    db.add(HiddenConversation(conversation_id=conversation_id, user_id=USER))
    db.commit()
    client.get(URL)
    assert len(hidden_ids(db)) == expected
    assert get_row(db).questions == NEW


def test_missing_rag_conversation_is_replaced(env):
    client, _, db, _ = env
    db.add(HiddenConversation(conversation_id=str(uuid4()), user_id=USER))
    db.commit()
    client.get(URL)
    assert len(hidden_ids(db)) == 2
    assert get_row(db).questions == NEW


def test_prompt_uses_experience_and_specialty(env):
    client, rag, db, _ = env
    db.add(UserSettings(user_id=USER, experience="fellow", specialty="Nephrology"))
    db.commit()
    client.get(URL)
    assert "a subspecialty fellow specializing in Nephrology" in rag.prompts[0]


def test_hidden_conversations_are_not_reachable_as_chats(env):
    client, rag, db, _ = env
    visible = rag.add()
    by_id = rag.add("Renamed by the RAG service")
    by_title = rag.add(chats.HIDDEN_CONVERSATION_TITLE)
    db.add(HiddenConversation(conversation_id=by_id, user_id=USER))
    db.commit()

    assert [chat["id"] for chat in client.get("/api/v1/chats").json()] == [visible]
    assert client.get(f"/api/v1/chats/{visible}").status_code == 200
    for hidden in (by_id, by_title):
        assert client.get(f"/api/v1/chats/{hidden}").status_code == 404
        assert client.post(f"/api/v1/chats/{hidden}/messages", json={"content": "hi"}).status_code == 404


def test_chat_message_returns_streamed_reply(env):
    client, rag, _, _ = env
    rag.reply = "An answer"
    response = client.post(f"/api/v1/chats/{rag.add()}/messages", json={"content": "A question"})
    assert response.status_code == 200
    assert (response.json()["role"], response.json()["content"]) == ("assistant", "An answer")


@pytest.mark.parametrize("status", [None, "pending", "failed"])
def test_chat_message_does_not_return_an_earlier_answer(env, status):
    client, rag, _, _ = env
    conversation_id = rag.add()
    rag.add_message(conversation_id, "assistant", "Earlier answer")
    rag.status = status
    response = client.post(f"/api/v1/chats/{conversation_id}/messages", json={"content": "A question"})
    assert response.status_code == 502


@pytest.mark.parametrize(
    "content",
    [
        '["A?", "B?", "C?"]',
        'Based on the sources [1], here you go:\n```json\n["A?", "B?", "C?"]\n```',
        '["A? [1]", "B? [2, 3]", " C? ", "a?", "", 5]',
        json.dumps(["A?", "x" * 121, "B?", "C?"]),
    ],
)
def test_parse_questions_accepts(content):
    assert suggestions.parse_questions(content) == ["A?", "B?", "C?"]


@pytest.mark.parametrize("content", ["", "No.", "[1]", '["A?", "B?"]', '["A?", "B?", "C?"', '{"a": 1}'])
def test_parse_questions_rejects(content):
    with pytest.raises(ValueError):
        suggestions.parse_questions(content)
