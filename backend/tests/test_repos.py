"""Phase 1.2 — repo import/list/detail/delete + status endpoint."""
from __future__ import annotations

import pytest
from app.services.github_repo import RepoMeta


@pytest.fixture
def auth(client):
    token = client.post("/api/auth/dev-login").json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _stub_network(monkeypatch):
    """Avoid real GitHub calls + real cloning in the CRUD tests."""
    async def _fake_meta(ref, token=None):
        return RepoMeta(
            default_branch="main",
            description="A test repo",
            stars=123,
            size_kb=42,
            private=False,
        )

    monkeypatch.setattr("app.api.repos.fetch_repo_meta", _fake_meta)
    monkeypatch.setattr("app.api.repos.enqueue_indexing", lambda *a, **k: None)


def _import(client, auth, url="https://github.com/tiangolo/fastapi"):
    return client.post("/api/repos/import", json={"github_url": url}, headers=auth)


def test_import_rejects_non_github_url(client, auth):
    resp = _import(client, auth, "https://gitlab.com/foo/bar")
    assert resp.status_code == 422


def test_import_rejects_ssrf_host(client, auth):
    resp = _import(client, auth, "https://github.com.evil.com/foo/bar")
    assert resp.status_code == 422


def test_import_creates_repo_and_job(client, auth):
    resp = _import(client, auth)
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "queued"
    assert body["repo_id"] and body["job_id"]


def test_list_and_detail(client, auth):
    repo_id = _import(client, auth).json()["repo_id"]
    listing = client.get("/api/repos", headers=auth).json()
    assert any(r["id"] == repo_id for r in listing)

    detail = client.get(f"/api/repos/{repo_id}", headers=auth).json()
    assert detail["description"] == "A test repo"
    assert detail["stars"] == 123


def test_status_endpoint(client, auth):
    repo_id = _import(client, auth).json()["repo_id"]
    status_body = client.get(f"/api/repos/{repo_id}/status", headers=auth).json()
    assert status_body["total"] == 7
    assert status_body["status"] == "queued"


def test_overview_conflict_before_ready(client, auth):
    repo_id = _import(client, auth).json()["repo_id"]
    assert client.get(f"/api/repos/{repo_id}/overview", headers=auth).status_code == 409


def test_delete(client, auth):
    repo_id = _import(client, auth).json()["repo_id"]
    assert client.delete(f"/api/repos/{repo_id}", headers=auth).status_code == 204
    assert client.get(f"/api/repos/{repo_id}", headers=auth).status_code == 404


def test_import_requires_auth(client):
    assert client.post("/api/repos/import", json={"github_url": "x"}).status_code == 401
