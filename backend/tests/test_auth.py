import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.auth import read_session_token
from app.database import get_db, settings
from app.main import app
from app.models import AuthSession, AuthUser, Base

SECRET = "test-secret-for-better-auth-cookies-0123456789"
COOKIE = "better-auth.session_token"


def sign(token: str, secret: str = SECRET) -> str:
    """Build a cookie value the way Better Auth does: url-encoded "<token>.<base64 HMAC-SHA256>"."""
    signature = base64.b64encode(hmac.new(secret.encode(), token.encode(), hashlib.sha256).digest()).decode()
    return quote(f"{token}.{signature}")


def test_read_session_token_accepts_valid_signature():
    assert read_session_token(sign("abc123"), SECRET) == "abc123"


@pytest.mark.parametrize("cookie_value", [
    sign("abc123").replace("abc123", "abc124"),  # tampered token
    sign("abc123", secret="some-other-secret"),  # signed with a different secret
    "abc123",                                    # no signature
    "",
])
def test_read_session_token_rejects_invalid_cookies(cookie_value):
    assert read_session_token(cookie_value, SECRET) is None


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A TestClient whose get_db uses a fresh SQLite database holding one user and two sessions."""
    monkeypatch.setattr(settings, "BETTER_AUTH_SECRET", SECRET)
    db_path = tmp_path / "auth.db"

    sync_engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    Base.metadata.create_all(sync_engine)
    now = datetime.now(timezone.utc)
    with Session(sync_engine) as db:
        db.add(AuthUser(id="user-1", name="Ada Clinician", email="ada@example.com", email_verified=False))
        db.add_all([
            AuthSession(id="s-live", token="live-token", user_id="user-1",
                        expires_at=now + timedelta(days=7), updated_at=now),
            AuthSession(id="s-expired", token="expired-token", user_id="user-1",
                        expires_at=now - timedelta(minutes=1), updated_at=now),
        ])
        db.commit()
    sync_engine.dispose()

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}", poolclass=NullPool)
    sessionmaker = async_sessionmaker(async_engine, expire_on_commit=False)

    async def test_db():
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_me_returns_user_for_live_session(client):
    client.cookies.set(COOKIE, sign("live-token"))
    response = client.get("/api/v1/me")

    assert response.status_code == 200
    assert response.json() == {"id": "user-1", "name": "Ada Clinician", "email": "ada@example.com"}


def test_me_accepts_secure_cookie_name(client):
    client.cookies.set(f"__Secure-{COOKIE}", sign("live-token"))
    response = client.get("/api/v1/me")

    assert response.status_code == 200


@pytest.mark.parametrize("cookies", [
    {},                                                          # no cookie
    {COOKIE: "live-token.not-a-real-signature"},                 # bad signature
    {COOKIE: sign("live-token", secret="some-other-secret")},    # signed with a different secret
    {COOKIE: sign("unknown-token")},                             # valid signature, no such session
    {COOKIE: sign("expired-token")},                             # valid signature, session expired
])
def test_me_rejects_invalid_sessions(client, cookies):
    client.cookies.update(cookies)
    response = client.get("/api/v1/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not signed in"}
