"""Learning roadmap model (Phase 2, schema defined up front)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.repo import Repo


class Roadmap(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "roadmaps"

    repo_id: Mapped[str] = mapped_column(
        ForeignKey("repos.id", ondelete="CASCADE"), index=True
    )
    # List of day objects: {day, title, tasks[], complete} — matches ROADMAP_DAYS.
    days: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    repo: Mapped[Repo] = relationship(back_populates="roadmaps")
