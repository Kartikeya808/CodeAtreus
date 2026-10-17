"""User settings schemas (Phase 4.5): profile, API keys, usage."""
from __future__ import annotations

from pydantic import BaseModel


class ProfileOut(BaseModel):
    id: str
    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    github_login: str | None = None
    github_connected: bool = False
    plan: str = "free"


class ProfileUpdate(BaseModel):
    name: str | None = None
    email: str | None = None


class ApiKeysOut(BaseModel):
    """Masked previews only — the raw keys are never returned."""
    openrouter_key: str | None = None  # masked preview or None when unset
    github_token: str | None = None
    openrouter_set: bool = False
    github_set: bool = False


class ApiKeysUpdate(BaseModel):
    # None = leave unchanged; "" = clear; any other value = set (stored encrypted).
    openrouter_key: str | None = None
    github_token: str | None = None


class UsageOut(BaseModel):
    repos_indexed: int
    questions_asked: int
    tokens_used: int
    plan: str
    token_budget: int  # 0 = unlimited
    monthly: list[MonthlyUsage]


class MonthlyUsage(BaseModel):
    month: str
    questions: int
    tokens: int


UsageOut.model_rebuild()
