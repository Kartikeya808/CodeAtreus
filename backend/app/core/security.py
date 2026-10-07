"""JWT issuance/verification and token types."""
from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import settings


class TokenType(str, enum.Enum):
    access = "access"
    refresh = "refresh"


def _now() -> datetime:
    return datetime.now(UTC)


def create_token(subject: str, token_type: TokenType, extra: dict[str, Any] | None = None) -> str:
    """Create a signed JWT for ``subject`` (the user id)."""
    if token_type is TokenType.access:
        expires = _now() + timedelta(minutes=settings.access_token_expire_minutes)
    else:
        expires = _now() + timedelta(days=settings.refresh_token_expire_days)

    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type.value,
        "iat": int(_now().timestamp()),
        "exp": int(expires.timestamp()),
        "jti": uuid.uuid4().hex,  # enables refresh-token rotation / revocation
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: TokenType | None = None) -> dict[str, Any]:
    """Decode + validate a JWT. Raises ``jwt.PyJWTError`` on any problem."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if expected_type is not None and payload.get("type") != expected_type.value:
        raise jwt.InvalidTokenError(
            f"expected {expected_type.value} token, got {payload.get('type')}"
        )
    return payload


def create_token_pair(subject: str) -> dict[str, Any]:
    """Issue an access + refresh token pair for a user id."""
    return {
        "access_token": create_token(subject, TokenType.access),
        "refresh_token": create_token(subject, TokenType.refresh),
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }
