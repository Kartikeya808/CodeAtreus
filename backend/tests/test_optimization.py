"""Phase 4.6 — LLM response cache, token-budget rate limiting, incremental re-index."""
from __future__ import annotations

import pytest
from app.models.repo import Repo, RepoStatus
from app.models.user import User
from app.services import llm, llm_cache
from app.services.github_repo import RepoMeta
from app.services.vectorstore import Chunk, VectorStore


@pytest.fixture
def auth(client):
    token = client.post("/api/auth/dev-login").json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── cache key ─────────────────────────────────────────────────────────────────
def test_cache_key_normalises_and_invalidates():
    k1 = llm_cache.make_key("r1", "sha1", "How does Auth work?")
    k2 = llm_cache.make_key("r1", "sha1", "how   does auth   WORK?")
    assert k1 == k2  # case + whitespace normalised
    # Different commit sha → different key (cache invalidates on re-index).
    assert llm_cache.make_key("r1", "sha2", "How does Auth work?") != k1
    # Different repo → different key.
    assert llm_cache.make_key("r2", "sha1", "How does Auth work?") != k1


def test_cache_put_get_roundtrip(db_session):
    user = User(github_login="c", name="C")
    db_session.add(user)
    db_session.commit()
    repo = Repo(owner_id=user.id, github_url="https://github.com/local/c.git",
                full_name="local/c", name="c", status=RepoStatus.ready)
    db_session.add(repo)
    db_session.commit()

    key = llm_cache.make_key(repo.id, None, "q")
    assert llm_cache.get(db_session, key) is None
    llm_cache.put(db_session, repo.id, key, "q", "an answer", ["a.py"])
    hit = llm_cache.get(db_session, key)
    assert hit is not None and hit.answer == "an answer" and hit.files == ["a.py"]


# ── chat cache integration ────────────────────────────────────────────────────
@pytest.fixture
def indexed_repo(client, auth, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.vectorstore.settings.chroma_persist_dir", str(tmp_path / "chroma")
    )
    user = db_session.query(User).first()
    repo = Repo(
        owner_id=user.id,
        github_url="https://github.com/local/x.git",
        full_name="local/x",
        name="x",
        status=RepoStatus.ready,
        chroma_collection="repo_test_opt",
        indexed_commit_sha="deadbeef",
    )
    db_session.add(repo)
    db_session.commit()
    VectorStore("repo_test_opt").add_chunks(
        [Chunk(id="a.py:1", path="a.py", content="def auth(): return 1")]
    )
    return repo


def test_chat_caches_llm_answers(client, auth, indexed_repo, monkeypatch):
    calls = {"n": 0}

    async def _fake_complete(question, blocks, api_key=None):
        calls["n"] += 1
        return {"answer": "cached answer", "usage": {"total_tokens": 12}}

    monkeypatch.setattr(llm, "complete", _fake_complete)

    r1 = client.post(f"/api/repos/{indexed_repo.id}/chat",
                     json={"message": "how does auth work"}, headers=auth)
    assert r1.status_code == 200 and r1.json()["answer"] == "cached answer"

    # Identical question → served from cache, LLM not called again.
    r2 = client.post(f"/api/repos/{indexed_repo.id}/chat",
                     json={"message": "how   does AUTH work"}, headers=auth)
    assert r2.status_code == 200 and r2.json()["answer"] == "cached answer"
    assert calls["n"] == 1


# ── rate limiting ─────────────────────────────────────────────────────────────
def test_token_budget_returns_429_when_exceeded(
    client, auth, indexed_repo, db_session, monkeypatch
):
    from app.models.chat import ChatMessage, ChatRole, ChatSession

    monkeypatch.setattr("app.core.config.settings.free_monthly_token_budget", 5)
    # Record an assistant turn this month that blows the tiny budget.
    session = ChatSession(repo_id=indexed_repo.id, title="s")
    db_session.add(session)
    db_session.commit()
    db_session.add(ChatMessage(session_id=session.id, role=ChatRole.assistant,
                               content="x", files=[], usage={"total_tokens": 99}))
    db_session.commit()

    resp = client.post(f"/api/repos/{indexed_repo.id}/chat",
                       json={"message": "anything"}, headers=auth)
    assert resp.status_code == 429


# ── incremental re-index skip ─────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _stub_import_network(monkeypatch):
    async def _fake_meta(ref, token=None):
        return RepoMeta(default_branch="main", description="d", stars=1, size_kb=1, private=False)
    monkeypatch.setattr("app.api.repos.fetch_repo_meta", _fake_meta)
    monkeypatch.setattr("app.api.repos.enqueue_indexing", lambda *a, **k: None)


def test_reimport_skips_when_commit_unchanged(client, auth, db_session, monkeypatch):
    user = db_session.query(User).first()
    repo = Repo(
        owner_id=user.id,
        github_url="https://github.com/local/skip.git",
        full_name="local/skip",
        name="skip",
        status=RepoStatus.ready,
        indexed_commit_sha="abc123",
    )
    db_session.add(repo)
    db_session.commit()

    monkeypatch.setattr("app.api.repos.remote_head_sha", lambda url, branch: "abc123")
    resp = client.post("/api/repos/import",
                       json={"github_url": "https://github.com/local/skip"}, headers=auth)
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "ready"
    assert body["job_id"] is None  # no re-index enqueued


def test_reimport_runs_when_commit_changed(client, auth, db_session, monkeypatch):
    user = db_session.query(User).first()
    repo = Repo(
        owner_id=user.id,
        github_url="https://github.com/local/changed.git",
        full_name="local/changed",
        name="changed",
        status=RepoStatus.ready,
        indexed_commit_sha="old",
    )
    db_session.add(repo)
    db_session.commit()

    monkeypatch.setattr("app.api.repos.remote_head_sha", lambda url, branch: "new")
    resp = client.post("/api/repos/import",
                       json={"github_url": "https://github.com/local/changed"}, headers=auth)
    assert resp.status_code == 202
    assert resp.json()["job_id"] is not None  # re-index enqueued
