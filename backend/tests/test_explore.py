"""Phase 3 — flow, sequence, search, api-docs."""
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
def ready_repo(client, auth, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.vectorstore.settings.chroma_persist_dir", str(tmp_path / "chroma")
    )
    user = db_session.query(User).first()
    repo = Repo(
        owner_id=user.id,
        github_url="https://github.com/local/shop.git",
        full_name="local/shop",
        name="shop",
        status=RepoStatus.ready,
        chroma_collection="repo_shop_explore",
        graph={
            "nodes": [
                {"id": "gw", "label": "API Gateway", "type": "api",
                 "x": 400, "y": 160, "path": "src/gateway.ts"},
                {"id": "ac", "label": "AuthController", "type": "controller",
                 "x": 160, "y": 280, "path": "src/auth/auth.controller.ts"},
                {"id": "as", "label": "AuthService", "type": "service",
                 "x": 80, "y": 400, "path": "src/auth/auth.service.ts"},
                {"id": "ur", "label": "UserRepo", "type": "repo",
                 "x": 120, "y": 520, "path": "src/users/user.repository.ts"},
            ],
            "edges": [["gw", "ac"], ["ac", "as"], ["as", "ur"]],
        },
    )
    db_session.add(repo)
    db_session.commit()

    VectorStore("repo_shop_explore").add_chunks(
        [
            Chunk(
                id="src/auth/auth.service.ts:42",
                path="src/auth/auth.service.ts",
                content="async validateUser(email, password) "
                "{ return this.userRepo.findByEmail(email); }",
                start_line=42,
            ),
        ]
    )
    return repo


def test_flow_trace(client, auth, ready_repo):
    resp = client.post(
        f"/api/repos/{ready_repo.id}/flow",
        json={"entrypoint": "POST /api/auth/login"},
        headers=auth,
    )
    assert resp.status_code == 200
    steps = resp.json()["steps"]
    assert steps[0]["type"] == "request"
    assert steps[-1]["type"] == "response"
    types = [s["type"] for s in steps]
    # Service + repo layers appear in order between the bookends.
    assert "service" in types and "repo" in types
    assert types.index("service") < types.index("repo")


def test_sequence_diagram(client, auth, ready_repo):
    resp = client.post(
        f"/api/repos/{ready_repo.id}/sequence", json={"entrypoint": None}, headers=auth
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mermaid"].startswith("sequenceDiagram")
    assert "participant Client" in body["mermaid"]
    assert body["plantuml"].startswith("@startuml")
    assert body["plantuml"].rstrip().endswith("@enduml")


def test_search(client, auth, ready_repo):
    resp = client.get(
        f"/api/repos/{ready_repo.id}/search", params={"q": "validateUser email"}, headers=auth
    )
    assert resp.status_code == 200
    results = resp.json()
    assert results
    top = results[0]
    assert top["file"] == "src/auth/auth.service.ts"
    assert top["path"] == "src/auth/"
    assert top["line"] == 42
    assert 1 <= top["relevance"] <= 100


def test_api_docs_empty_without_clone(client, auth, ready_repo):
    resp = client.get(f"/api/repos/{ready_repo.id}/api-docs", headers=auth)
    assert resp.status_code == 200
    body = resp.json()
    assert body["openapi"] == "3.0.0"
    assert body["paths"] == {}  # no local clone in this test


def test_flow_409_when_not_ready(client, auth, db_session):
    user = db_session.query(User).first()
    repo = Repo(
        owner_id=user.id,
        github_url="https://github.com/local/w.git",
        full_name="local/w",
        name="w",
        status=RepoStatus.queued,
    )
    db_session.add(repo)
    db_session.commit()
    resp = client.post(f"/api/repos/{repo.id}/flow", json={}, headers=auth)
    assert resp.status_code == 409
