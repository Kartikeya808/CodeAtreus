"""Cached LLM chat answers (Phase 4.6).

Keyed by a hash of (repo_id + indexed commit sha + normalised question) so the
cache invalidates naturally when a repo is re-indexed at a new commit.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class LLMCache(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "llm_cache"

    cache_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    repo_id: Mapped[str] = mapped_column(
        ForeignKey("repos.id", ondelete="CASCADE"), index=True
    )
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    files: Mapped[list[Any]] = mapped_column(JSON, default=list)
