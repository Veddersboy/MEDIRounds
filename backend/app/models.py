from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def make_id() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


# Better Auth tables. Columns mirror the schema from `npx auth generate` (better-auth 1.7.13);
# Better Auth generates IDs and writes rows itself, so there are no Python-side defaults.
class AuthUser(Base):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    email_verified: Mapped[bool] = mapped_column("emailVerified", Boolean, nullable=False)
    image: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), nullable=False)
    sessions: Mapped[list["ChatSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    settings: Mapped["UserSettings | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class AuthSession(Base):
    __tablename__ = "session"
    __table_args__ = (Index("session_userId_idx", "userId"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    expires_at: Mapped[datetime] = mapped_column("expiresAt", DateTime(timezone=True), nullable=False)
    token: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), nullable=False)
    ip_address: Mapped[str | None] = mapped_column("ipAddress", Text, nullable=True)
    user_agent: Mapped[str | None] = mapped_column("userAgent", Text, nullable=True)
    user_id: Mapped[str] = mapped_column("userId", Text, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)


class AuthAccount(Base):
    __tablename__ = "account"
    __table_args__ = (Index("account_userId_idx", "userId"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    account_id: Mapped[str] = mapped_column("accountId", Text, nullable=False)
    provider_id: Mapped[str] = mapped_column("providerId", Text, nullable=False)
    user_id: Mapped[str] = mapped_column("userId", Text, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    access_token: Mapped[str | None] = mapped_column("accessToken", Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column("refreshToken", Text, nullable=True)
    id_token: Mapped[str | None] = mapped_column("idToken", Text, nullable=True)
    access_token_expires_at: Mapped[datetime | None] = mapped_column("accessTokenExpiresAt", DateTime(timezone=True), nullable=True)
    refresh_token_expires_at: Mapped[datetime | None] = mapped_column("refreshTokenExpiresAt", DateTime(timezone=True), nullable=True)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    password: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), nullable=False)


class AuthVerification(Base):
    __tablename__ = "verification"
    __table_args__ = (Index("verification_identifier_idx", "identifier"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    identifier: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column("expiresAt", DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), nullable=False)


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (Index("ix_chat_sessions_user_updated", "user_id", "updated_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=make_id)
    user_id: Mapped[str] = mapped_column(Text, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="New conversation", nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user: Mapped[AuthUser] = relationship(back_populates="sessions")
    messages: Mapped[list["Message"]] = relationship(back_populates="session", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_session_created", "session_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=make_id)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    message_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    session: Mapped[ChatSession] = relationship(back_populates="messages")
    citations: Mapped[list["Citation"]] = relationship(back_populates="message", cascade="all, delete-orphan")


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=make_id)
    message_id: Mapped[str] = mapped_column(String(36), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    message: Mapped[Message] = relationship(back_populates="citations")


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(Text, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    theme: Mapped[str] = mapped_column(String(16), default="system", nullable=False)
    clinician_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    specialty: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    show_disclaimer: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enter_to_send: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    user: Mapped[AuthUser] = relationship(back_populates="settings")
