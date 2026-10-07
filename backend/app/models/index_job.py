"""Indexing job tracking — drives the 7-step pipeline progress UI."""
from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.repo import Repo

# Matches PIPELINE_STEPS in the frontend (src/App.tsx).
TOTAL_STEPS = 7
PIPELINE_LABELS = [
    "Git Clone",
    "AST Parsing",
    "Metadata Extraction",
    "Embedding Generation",
    "Dependency Analysis",
    "Knowledge Graph",
    "Ready",
]


class IndexStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    ready = "ready"
    failed = "failed"


class IndexJob(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "index_jobs"

    repo_id: Mapped[str] = mapped_column(
        ForeignKey("repos.id", ondelete="CASCADE"), index=True
    )

    status: Mapped[IndexStatus] = mapped_column(
        SAEnum(IndexStatus, native_enum=False, length=16),
        default=IndexStatus.queued,
    )
    step: Mapped[int] = mapped_column(Integer, default=0)   # 0..7
    total: Mapped[int] = mapped_column(Integer, default=TOTAL_STEPS)
    label: Mapped[str] = mapped_column(String(128), default="Queued")

    # Rolling list of human-readable log lines for the indexing page.
    logs: Mapped[list[str]] = mapped_column(JSON, default=list)
    error: Mapped[str | None] = mapped_column(String(2048), default=None)

    # Celery task id, for cancellation / inspection.
    task_id: Mapped[str | None] = mapped_column(String(128), default=None)

    extra: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)

    repo: Mapped[Repo] = relationship(back_populates="jobs")
