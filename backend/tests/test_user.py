"""Phase 4.5 — user settings: profile, API keys, usage, danger zone."""
from __future__ import annotations

import pytest
from app.services import crypto


@pytest.fixture
def auth(client):
    token = client.post("/api/auth/dev-login").json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── crypto ───────────────────────────────────────────────────────────────────
def test_crypto_roundtrip():
    secret = "sk-or-v1-supersecret-value"
    enc = crypto.encrypt(secret)
    assert enc.startswith("enc:")
    assert secret not in enc
    assert crypto.decrypt(enc) == secret


def test_crypto_passes_through_plaintext():
    # Legacy plaintext tokens (no enc: prefix) decrypt to themselves.
    assert crypto.decrypt("ghp_legacyplaintext") == "ghp_legacyplaintext"
    assert crypto.decrypt(None) is None


def test_crypto_mask():
    assert crypto.mask(None) is None
    masked = crypto.mask("sk-or-abcdefgh", visible=4)
    assert masked and "••••" in masked and masked.startswith("sk-o")


# ── profile ──────────────────────────────────────────────────────────────────
def test_get_and_update_profile(client, auth):
    prof = client.get("/api/user/profile", headers=auth).json()
    assert prof["plan"] == "free"
    assert prof["github_connected"] is False

    updated = client.put(
        "/api/user/profile", json={"name": "Ada", "email": "ada@x.io"}, headers=auth
    ).json()
    assert updated["name"] == "Ada"
    assert updated["email"] == "ada@x.io"


# ── api keys ─────────────────────────────────────────────────────────────────
def test_api_keys_set_masked_and_never_leaked(client, auth):
    raw = "sk-or-v1-0123456789abcdef"
    resp = client.put("/api/user/api-keys", json={"openrouter_key": raw}, headers=auth)
    assert resp.status_code == 200
    body = resp.json()
    assert body["openrouter_set"] is True
    # The raw key must never be returned — only a masked preview.
    assert body["openrouter_key"] != raw
    assert "••••" in body["openrouter_key"]

    # Re-fetch stays masked.
    again = client.get("/api/user/api-keys", headers=auth).json()
    assert again["openrouter_set"] is True
    assert again["openrouter_key"] != raw


def test_api_keys_stored_encrypted(client, auth, db_session):
    from app.models.user import User

    raw = "sk-or-v1-plaintextcheck"
    client.put("/api/user/api-keys", json={"openrouter_key": raw}, headers=auth)
    user = db_session.query(User).filter(User.github_login == "dev").one()
    assert user.openrouter_api_key is not None
    assert raw not in user.openrouter_api_key  # not plaintext at rest
    assert crypto.decrypt(user.openrouter_api_key) == raw


def test_api_keys_clear(client, auth):
    client.put("/api/user/api-keys", json={"openrouter_key": "sk-or-xyz"}, headers=auth)
    cleared = client.put("/api/user/api-keys", json={"openrouter_key": ""}, headers=auth).json()
    assert cleared["openrouter_set"] is False
    assert cleared["openrouter_key"] is None


# ── usage ────────────────────────────────────────────────────────────────────
def test_usage_shape(client, auth):
    usage = client.get("/api/user/usage", headers=auth).json()
    assert usage["repos_indexed"] == 0
    assert usage["questions_asked"] == 0
    assert usage["plan"] == "free"
    assert usage["token_budget"] == 2_000_000
    assert isinstance(usage["monthly"], list) and usage["monthly"]


# ── danger zone ──────────────────────────────────────────────────────────────
def test_reset_data_keeps_account(client, auth):
    assert client.delete("/api/user/data", headers=auth).status_code == 204
    # Account still usable.
    assert client.get("/api/user/profile", headers=auth).status_code == 200


def test_delete_account(client, auth):
    assert client.delete("/api/user", headers=auth).status_code == 204
    # Token now maps to a missing user → 401.
    assert client.get("/api/user/profile", headers=auth).status_code == 401
