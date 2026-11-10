from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.auth import get_current_user
from app.database import get_db, settings
from app.main import app
from app.models import AuthSession, AuthUser, Base, UserSettings
from tests.test_auth import COOKIE, SECRET, sign


@pytest.fixture
def settings_client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BETTER_AUTH_SECRET", SECRET)
    db_path = tmp_path / "settings_test.db"

    sync_engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    Base.metadata.create_all(sync_engine)
    now = datetime.now(timezone.utc)
    with Session(sync_engine) as db:
        db.add(AuthUser(id="user-settings-1", name="Dr. Smith", email="smith@example.com", email_verified=False))
        db.add(
            AuthSession(
                id="s-settings",
                token="settings-token",
                user_id="user-settings-1",
                expires_at=now + timedelta(days=7),
                updated_at=now,
            )
        )
        db.commit()
    sync_engine.dispose()

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}", poolclass=NullPool)
    sessionmaker = async_sessionmaker(async_engine, expire_on_commit=False)

    async def test_db():
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    client = TestClient(app)
    client.cookies.set(COOKIE, sign("settings-token"))
    yield client, sessionmaker
    app.dependency_overrides.clear()


def test_get_settings_default_experience(settings_client):
    client, _ = settings_client
    response = client.get("/api/v1/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["experience"] == ""


def test_experience_level_persists_between_sessions(settings_client):
    client, sessionmaker = settings_client

    # 1. Save settings with experience level "resident"
    save_payload = {
        "theme": "dark",
        "clinicianName": "Dr. Smith",
        "specialty": "Endocrinology",
        "showDisclaimer": True,
        "enterToSend": True,
        "experience": "resident",
    }
    put_response = client.put("/api/v1/settings", json=save_payload)
    assert put_response.status_code == 200
    assert put_response.json()["experience"] == "resident"

    # 2. Subsequent GET request (new request session) must return the persisted experience level
    get_response = client.get("/api/v1/settings")
    assert get_response.status_code == 200
    assert get_response.json()["experience"] == "resident"

    # 3. Update to "fellow" and verify persistence
    save_payload["experience"] = "fellow"
    put_response2 = client.put("/api/v1/settings", json=save_payload)
    assert put_response2.status_code == 200
    assert put_response2.json()["experience"] == "fellow"

    get_response2 = client.get("/api/v1/settings")
    assert get_response2.status_code == 200
    assert get_response2.json()["experience"] == "fellow"


def test_invalid_experience_rejected(settings_client):
    client, _ = settings_client
    bad_payload = {
        "theme": "light",
        "clinicianName": "",
        "specialty": "",
        "showDisclaimer": True,
        "enterToSend": True,
        "experience": "invalid_level",
    }
    response = client.put("/api/v1/settings", json=bad_payload)
    assert response.status_code == 422
