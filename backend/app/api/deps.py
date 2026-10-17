"""Shared FastAPI dependencies: current-user resolution from a bearer JWT."""
from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import TokenType, decode_token
from app.db.session import get_db
from app.models.user import User

# auto_error=False so we can raise a consistent 401 ourselves.
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(creds.credentials, expected_type=TokenType.access)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = db.get(User, payload.get("sub"))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def enforce_token_budget(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Reject requests once a user exceeds their monthly LLM-token budget.

    DB-backed (no Redis): the budget is derived from the user's plan and the
    tokens already recorded on this month's assistant messages. A plan budget of
    0 means unlimited. Users with their own OpenRouter key are never limited.
    """
    from app.services import crypto, usage

    if crypto.decrypt(user.openrouter_api_key):
        return user  # BYO key — not on our budget
    budget = usage.token_budget(user.plan)
    if budget and usage.tokens_used_this_month(db, user.id) >= budget:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly token budget exceeded. Add your own OpenRouter key in "
            "Settings to continue.",
        )
    return user
