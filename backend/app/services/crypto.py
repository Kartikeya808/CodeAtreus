"""Symmetric encryption for secrets at rest (BYO API keys, GitHub tokens).

Uses Fernet (AES-128-CBC + HMAC). The key is derived from ``settings.encryption_key``
when set, otherwise deterministically from ``settings.jwt_secret`` so existing
deployments keep working without provisioning a new env var. Values are stored
as opaque ``enc:<token>`` strings; :func:`decrypt` transparently passes through
any value lacking that prefix (e.g. a legacy plaintext token).
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("crypto")

_PREFIX = "enc:"


def _fernet() -> Fernet:
    raw = settings.encryption_key or settings.jwt_secret
    # Fernet needs a 32-byte urlsafe-base64 key; derive one deterministically.
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(plaintext: str) -> str:
    """Encrypt a secret, returning an ``enc:<token>`` string."""
    token = _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")
    return f"{_PREFIX}{token}"


def decrypt(value: str | None) -> str | None:
    """Decrypt a stored value. Passes plaintext (non-prefixed) values through."""
    if not value:
        return None
    if not value.startswith(_PREFIX):
        return value  # legacy/plaintext — return as-is
    try:
        return _fernet().decrypt(value[len(_PREFIX) :].encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.warning("failed to decrypt stored secret (key rotated?)")
        return None


def mask(value: str | None, *, visible: int = 4) -> str | None:
    """Render a short masked preview of a secret (e.g. ``sk-or-••••abcd``).

    Returns None when there is no value, so callers can signal "unset".
    """
    if not value:
        return None
    if len(value) <= visible:
        return "•" * 8
    return f"{value[:visible]}••••{value[-visible:]}"
