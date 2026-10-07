"""Auth endpoints: GitHub OAuth login, token refresh, current user.

Also exposes a guarded dev-login (``POST /auth/dev-login``) that is only active
outside production, so the frontend can be wired end-to-end before real GitHub
OAuth credentials are provisioned.
"""
from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import TokenType, create_token_pair, decode_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    GithubCallbackRequest,
    RefreshRequest,
    TokenPair,
    UserOut,
)
from app.services.github_oauth import GithubOAuthError, exchange_code_for_profile

router = APIRouter()


def _upsert_github_user(db: Session, profile) -> User:
    user = db.scalar(select(User).where(User.github_id == profile.github_id))
    if user is None:
        user = User(github_id=profile.github_id)
        db.add(user)
    user.github_login = profile.login
    user.name = profile.name
    user.email = profile.email
    user.avatar_url = profile.avatar_url
    user.github_access_token = profile.access_token
    db.commit()
    db.refresh(user)
    return user


@router.post("/github", response_model=TokenPair)
async def github_login(body: GithubCallbackRequest, db: Session = Depends(get_db)) -> TokenPair:
    """Exchange a GitHub OAuth `code` for CodeAtreus access + refresh tokens."""
    try:
        profile = await exchange_code_for_profile(body.code, body.redirect_uri)
    except GithubOAuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    user = _upsert_github_user(db, profile)
    return TokenPair(**create_token_pair(user.id))


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    """Rotate a refresh token into a fresh access + refresh pair."""
    try:
        payload = decode_token(body.refresh_token, expected_type=TokenType.refresh)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {exc}",
        ) from exc

    user = db.get(User, payload.get("sub"))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    # New jti on each issue => rotation (old refresh token can be denylisted later).
    return TokenPair(**create_token_pair(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/dev-login", response_model=TokenPair)
def dev_login(db: Session = Depends(get_db)) -> TokenPair:
    """Create/return a throwaway local user and issue tokens. Non-production only."""
    if settings.is_production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    user = db.scalar(select(User).where(User.github_login == "dev"))
    if user is None:
        user = User(
            github_login="dev",
            name="Dev User",
            email="dev@codeatreus.local",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return TokenPair(**create_token_pair(user.id))
