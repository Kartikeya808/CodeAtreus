"""Indexing status + overview response schemas."""
from __future__ import annotations

from pydantic import BaseModel

from app.models.index_job import IndexStatus


class IndexStatusOut(BaseModel):
    """Drives the `indexing` page's 7-step progress UI."""
    status: IndexStatus
    step: int
    total: int
    label: str
    logs: list[str]
    error: str | None = None


class LangSlice(BaseModel):
    name: str
    value: int
    color: str


class OverviewOut(BaseModel):
    """Matches the `overview` page data (LANG_DIST + metadata)."""
    language_dist: list[LangSlice]
    framework: str
    file_count: int
    size: str
    health: int
    entry_points: list[str]
    key_files: list[str]
