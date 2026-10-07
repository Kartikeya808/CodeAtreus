"""Chat session + message models."""
from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.repo import Repo


class ChatRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class ChatSession(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "chat_sessions"

    repo_id: Mapped[str] = mapped_column(
        ForeignKey("repos.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str | None] = mapped_column(String(255), default=None)

    repo: Mapped[Repo] = relationship(back_populates="chat_sessions")
    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "chat_messages"

    session_id: Mapped[str] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[ChatRole] = mapped_column(
        SAEnum(ChatRole, native_enum=False, length=16)
    )
    content: Mapped[str] = mapped_column(Text)

    # Cited file paths rendered as chips in the UI (matches CHAT_MESSAGES.files).
    files: Mapped[list[str]] = mapped_column(JSON, default=list)
    # Token accounting for usage limits / cost control.
    usage: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)

    session: Mapped[ChatSession] = relationship(back_populates="messages")
