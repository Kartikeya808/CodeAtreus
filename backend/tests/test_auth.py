"""Phase 1.1 — auth flow tests (dev-login, me, refresh, token-type guard)."""
from __future__ import annotations


def test_dev_login_issues_token_pair(client):
    resp = client.post("/api/auth/dev-login")
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_token(client):
    access = client.post("/api/auth/dev-login").json()["access_token"]
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200
    assert resp.json()["github_login"] == "dev"


def test_refresh_rotates_tokens(client):
    refresh = client.post("/api/auth/dev-login").json()["refresh_token"]
    resp = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_refresh_rejects_access_token(client):
    access = client.post("/api/auth/dev-login").json()["access_token"]
    # An access token must not be accepted where a refresh token is expected.
    resp = client.post("/api/auth/refresh", json={"refresh_token": access})
    assert resp.status_code == 401
