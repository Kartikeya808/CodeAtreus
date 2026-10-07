"""Phase 1.5 — grounded chat over an indexed repo (offline LLM fallback)."""
from __future__ import annotations

import pytest
from app.models.repo import Repo, RepoStatus
from app.models.user import User
from app.services.vectorstore import Chunk, VectorStore


@pytest.fixture
def auth(client):
    token = client.post("/api/auth/dev-login").json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def indexed_repo(client, auth, db_session, tmp_path, monkeypatch):
    """Create a ready repo with a populated (keyword) vector collection."""
    monkeypatch.setattr(
        "app.services.vectorstore.settings.chroma_persist_dir", str(tmp_path / "chroma")
    )
    user = db_session.query(User).first()  # the dev user created via `auth`
    collection = "repo_test_chat"
    repo = Repo(
        owner_id=user.id,
        github_url="https://github.com/local/x.git",
        full_name="local/x",
        name="x",
        status=RepoStatus.ready,
        chroma_collection=collection,
    )
    db_session.add(repo)
    db_session.commit()

    store = VectorStore(collection)
    store.add_chunks(
        [
            Chunk(
                id="src/auth/auth.service.ts:1",
                path="src/auth/auth.service.ts",
                content="class AuthService { validateUser(email, password) "
                "{ return bcrypt.compare(password); } }",
            ),
            Chunk(
                id="src/payments/stripe.service.ts:1",
                path="src/payments/stripe.service.ts",
                content="class StripeService { createPaymentIntent(amount) "
                "{ return stripe.create(); } }",
            ),
        ]
    )
    return repo


def test_chat_grounded_answer_cites_relevant_file(client, auth, indexed_repo):
    resp = client.post(
        f"/api/repos/{indexed_repo.id}/chat",
        json={"message": "how does authentication validateUser work"},
        headers=auth,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "src/auth/auth.service.ts" in body["files"]
    assert body["answer"]


def test_chat_history_records_turns(client, auth, indexed_repo):
    client.post(
        f"/api/repos/{indexed_repo.id}/chat",
        json={"message": "payment stripe"},
        headers=auth,
    )
    history = client.get(f"/api/repos/{indexed_repo.id}/chat/history", headers=auth).json()
    roles = [m["role"] for m in history]
    assert roles == ["user", "assistant"]
    assert "src/payments/stripe.service.ts" in history[1]["files"]


def test_chat_409_when_repo_not_ready(client, auth, db_session):
    user = db_session.query(User).first()
    repo = Repo(
        owner_id=user.id,
        github_url="https://github.com/local/y.git",
        full_name="local/y",
        name="y",
        status=RepoStatus.indexing,
    )
    db_session.add(repo)
    db_session.commit()
    resp = client.post(
        f"/api/repos/{repo.id}/chat", json={"message": "hi"}, headers=auth
    )
    assert resp.status_code == 409
