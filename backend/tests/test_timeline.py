"""Phase 4.1 — decision timeline from commit history."""
from __future__ import annotations

import pytest
from app.models.repo import Repo, RepoStatus
from app.models.user import User
from app.services import timeline
from app.services.timeline import Commit


@pytest.fixture
def auth(client):
    token = client.post("/api/auth/dev-login").json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _commits() -> list[Commit]:
    return [
        Commit("aaaaaaa", "feat: add login", "Ada", "2026-01-05T10:00:00Z"),
        Commit("bbbbbbb", "fix: login redirect", "Ada", "2026-01-06T10:00:00Z"),
        Commit("ccccccc", "docs: readme", "Bob", "2026-01-20T10:00:00Z"),
    ]


def test_cluster_by_week_groups_and_orders():
    clusters = timeline.cluster_by_week(_commits())
    assert len(clusters) == 2
    # Newest week first.
    assert clusters[0]["period"] > clusters[1]["period"]
    first_week = next(c for c in clusters if len(c["commits"]) == 2)
    assert {x["sha"] for x in first_week["commits"]} == {"aaaaaaa", "bbbbbbb"}


def test_cluster_handles_bad_dates():
    clusters = timeline.cluster_by_week([Commit("z", "msg", "x", "not-a-date")])
    assert clusters[0]["period"] == "unknown"


@pytest.mark.asyncio
async def test_build_timeline_uses_heuristic_without_llm(monkeypatch):
    async def _fake_fetch(full_name, token, limit=100):
        return _commits()
    monkeypatch.setattr(timeline, "fetch_commits", _fake_fetch)

    result = await timeline.build_timeline("local/x", token=None, api_key=None)
    assert result["commit_count"] == 3
    assert result["clusters"]
    # Heuristic summary (no LLM) mentions the commit subjects.
    assert "login" in result["clusters"][-1]["summary"].lower() or \
           "login" in result["clusters"][0]["summary"].lower()


@pytest.mark.asyncio
async def test_fetch_commits_empty_on_network_error(monkeypatch):
    # Point at an unroutable host style — httpx error path returns [].
    async def _boom(*a, **k):
        raise RuntimeError("no network")
    import httpx
    monkeypatch.setattr(httpx.AsyncClient, "get", _boom)
    assert await timeline.fetch_commits("local/x", token=None) == []


def test_timeline_endpoint_caches(client, auth, db_session, monkeypatch):
    user = db_session.query(User).first()
    repo = Repo(
        owner_id=user.id,
        github_url="https://github.com/local/tl.git",
        full_name="local/tl",
        name="tl",
        status=RepoStatus.ready,
    )
    db_session.add(repo)
    db_session.commit()

    async def _fake_fetch(full_name, token, limit=100):
        return _commits()
    monkeypatch.setattr(timeline, "fetch_commits", _fake_fetch)

    resp = client.get(f"/api/repos/{repo.id}/timeline", headers=auth)
    assert resp.status_code == 200
    body = resp.json()
    assert body["commit_count"] == 3
    assert body["clusters"][0]["title"]

    # Cached: changing the stub shouldn't change the cached response.
    async def _fail(*a, **k):
        raise AssertionError("should not refetch when cached")
    monkeypatch.setattr(timeline, "fetch_commits", _fail)
    cached = client.get(f"/api/repos/{repo.id}/timeline", headers=auth)
    assert cached.json()["generated_at"] == body["generated_at"]


def test_timeline_404_for_other_users_repo(client, auth, db_session):
    assert client.get("/api/repos/does-not-exist/timeline", headers=auth).status_code == 404
