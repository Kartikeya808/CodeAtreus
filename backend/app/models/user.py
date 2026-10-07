"""User + OAuth identity model."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.repo import Repo


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    # GitHub identity.
    github_id: Mapped[int | None] = mapped_column(unique=True, index=True, default=None)
    github_login: Mapped[str | None] = mapped_column(String(255), default=None)
    email: Mapped[str | None] = mapped_column(String(320), index=True, default=None)
    name: Mapped[str | None] = mapped_column(String(255), default=None)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), default=None)

    # Encrypted GitHub access token (for private-repo clone + API calls).
    github_access_token: Mapped[str | None] = mapped_column(String(512), default=None)

    # BYO OpenRouter key (Phase 4 settings page); nullable until set.
    openrouter_api_key: Mapped[str | None] = mapped_column(String(512), default=None)

    plan: Mapped[str] = mapped_column(String(32), default="free")

    repos: Mapped[list[Repo]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
