"""Repository Pydantic schemas (request + response shapes for the UI)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.repo import RepoStatus


class RepoImportRequest(BaseModel):
    github_url: str = Field(..., examples=["https://github.com/tiangolo/fastapi"])


class RepoImportResponse(BaseModel):
    """202-style response the `import` page uses to transition to `indexing`."""
    repo_id: str
    status: RepoStatus
    job_id: str | None = None


class RepoOut(BaseModel):
    """Dashboard/overview card shape — mirrors the frontend `Repo` interface."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    language: str
    framework: str
    stars: int
    lastIndexed: str  # noqa: N815 - matches the frontend field name
    health: int
    description: str
    color: str
    files: int
    size: str
    status: RepoStatus
