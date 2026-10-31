import base64
import hashlib
import hmac
from datetime import datetime, timezone
from urllib.parse import unquote

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, settings
from app.models import AuthSession, AuthUser

COOKIE_NAMES = ("__Secure-better-auth.session_token", "better-auth.session_token")

def read_session_token(cookie_value: str, secret: str) -> str | None:
    """Return the session token if the cookie's signature is valid."""
    token, _, signature = unquote(cookie_value).rpartition(".")
    if not token:
        return None
    expected = base64.b64encode(hmac.new(secret.encode(), token.encode(), hashlib.sha256).digest()).decode()
    return token if hmac.compare_digest(signature, expected) else None


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> AuthUser:
    cookie = next((request.cookies[name] for name in COOKIE_NAMES if name in request.cookies), None)
    token = cookie and read_session_token(cookie, settings.BETTER_AUTH_SECRET)
    user = token and await db.scalar(
        select(AuthUser)
        .join(AuthSession, AuthSession.user_id == AuthUser.id)
        .where(AuthSession.token == token, AuthSession.expires_at > datetime.now(timezone.utc))
    )
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    return user