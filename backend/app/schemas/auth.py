"""Auth + user Pydantic schemas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class GithubCallbackRequest(BaseModel):
    """Body for POST /api/auth/github — the `code` from GitHub's OAuth redirect."""
    code: str
    redirect_uri: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    github_login: str | None = None
    email: str | None = None
    name: str | None = None
    avatar_url: str | None = None
    plan: str = "free"
