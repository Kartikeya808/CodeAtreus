"""Repository model + indexed metadata."""
from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.chat import ChatSession
    from app.models.index_job import IndexJob
    from app.models.roadmap import Roadmap
    from app.models.user import User


class RepoStatus(str, enum.Enum):
    queued = "queued"
    indexing = "indexing"
    ready = "ready"
    failed = "failed"


class Repo(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "repos"

    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    # Source.
    github_url: Mapped[str] = mapped_column(String(1024))
    full_name: Mapped[str] = mapped_column(String(512), index=True)  # "owner/name"
    name: Mapped[str] = mapped_column(String(255))
    default_branch: Mapped[str] = mapped_column(String(255), default="main")
    description: Mapped[str | None] = mapped_column(Text, default=None)
    stars: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[RepoStatus] = mapped_column(
        SAEnum(RepoStatus, native_enum=False, length=16),
        default=RepoStatus.queued,
        index=True,
    )

    # Denormalised overview metadata (populated by the indexing pipeline).
    primary_language: Mapped[str | None] = mapped_column(String(64), default=None)
    framework: Mapped[str | None] = mapped_column(String(64), default=None)
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    health_score: Mapped[int | None] = mapped_column(Integer, default=None)

    # Rich JSON blobs: language_dist, entry_points, key_files, symbol summary, etc.
    overview: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    # NetworkX dependency graph serialised as {nodes, edges}.
    graph: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    # Cached LLM architecture summary (regenerated on re-index). {modules:[...], summary}
    architecture: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)

    # Local clone path + chroma collection name.
    local_path: Mapped[str | None] = mapped_column(String(1024), default=None)
    chroma_collection: Mapped[str | None] = mapped_column(String(128), default=None)

    owner: Mapped[User] = relationship(back_populates="repos")
    jobs: Mapped[list[IndexJob]] = relationship(
        back_populates="repo", cascade="all, delete-orphan"
    )
    chat_sessions: Mapped[list[ChatSession]] = relationship(
        back_populates="repo", cascade="all, delete-orphan"
    )
    roadmaps: Mapped[list[Roadmap]] = relationship(
        back_populates="repo", cascade="all, delete-orphan"
    )
