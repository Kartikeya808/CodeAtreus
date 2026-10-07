"""Phase 2 — architecture, important-files, roadmap, graph, dashboard."""
from __future__ import annotations

import pytest
from app.models.repo import Repo, RepoStatus
from app.models.user import User


@pytest.fixture
def auth(client):
    token = client.post("/api/auth/dev-login").json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def ready_repo(client, auth, db_session):
    """A ready repo with representative overview + graph JSON."""
    user = db_session.query(User).first()
    repo = Repo(
        owner_id=user.id,
        github_url="https://github.com/local/shop.git",
        full_name="local/shop",
        name="shop",
        status=RepoStatus.ready,
        primary_language="TypeScript",
        file_count=120,
        chroma_collection="repo_shop",
        overview={
            "language_dist": [{"name": "TypeScript", "value": 100, "color": "#3b82f6"}],
            "framework": "Next.js",
            "file_count": 120,
            "size": "3.0 MB",
            "health": 90,
            "entry_points": ["src/main.tsx"],
            "key_files": ["package.json", "tsconfig.json", "README.md"],
        },
        graph={
            "nodes": [
                {"id": "ac", "label": "AuthController", "type": "controller",
                 "x": 160, "y": 280, "path": "src/auth/auth.controller.ts"},
                {"id": "as", "label": "AuthService", "type": "service",
                 "x": 80, "y": 400, "path": "src/auth/auth.service.ts"},
                {"id": "ur", "label": "UserRepo", "type": "repo",
                 "x": 120, "y": 520, "path": "src/users/user.repository.ts"},
            ],
            "edges": [["ac", "as"], ["as", "ur"]],
        },
    )
    db_session.add(repo)
    db_session.commit()
    return repo


def test_architecture_summary(client, auth, ready_repo):
    resp = client.post(f"/api/repos/{ready_repo.id}/architecture-summary", headers=auth)
    assert resp.status_code == 200
    body = resp.json()
    assert body["modules"]
    layers = {m["layer"] for m in body["modules"]}
    assert {"controller", "service", "repo"} <= layers


def test_important_files(client, auth, ready_repo):
    resp = client.get(f"/api/repos/{ready_repo.id}/important-files", headers=auth)
    assert resp.status_code == 200
    files = resp.json()
    paths = {f["path"] for f in files}
    assert "package.json" in paths
    pkg = next(f for f in files if f["path"] == "package.json")
    assert "config" in pkg["tags"]


def test_graph_endpoint(client, auth, ready_repo):
    resp = client.get(f"/api/repos/{ready_repo.id}/graph", headers=auth)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["nodes"]) == 3
    assert body["edges"] == [["ac", "as"], ["as", "ur"]]
    assert body["colors"]["service"] == "#10b981"


def test_roadmap_lazy_generation(client, auth, ready_repo):
    resp = client.get(f"/api/repos/{ready_repo.id}/roadmap", headers=auth)
    assert resp.status_code == 200
    days = resp.json()["days"]
    assert len(days) == 5
    assert days[0]["day"] == 1 and days[0]["tasks"]


def test_roadmap_regenerate(client, auth, ready_repo):
    resp = client.post(f"/api/repos/{ready_repo.id}/roadmap/generate", headers=auth)
    assert resp.status_code == 200
    assert len(resp.json()["days"]) == 5


def test_dashboard_stats_and_activity(client, auth, ready_repo):
    stats = client.get("/api/dashboard/stats", headers=auth).json()
    assert stats["repos_indexed"] == 1
    assert stats["questions_asked"] == 0

    activity = client.get("/api/dashboard/activity", headers=auth).json()
    assert len(activity) == 7
    # The current month should reflect the one imported repo.
    assert activity[-1]["repos"] == 1


def test_analysis_409_when_not_ready(client, auth, db_session):
    user = db_session.query(User).first()
    repo = Repo(
        owner_id=user.id,
        github_url="https://github.com/local/z.git",
        full_name="local/z",
        name="z",
        status=RepoStatus.indexing,
    )
    db_session.add(repo)
    db_session.commit()
    assert client.get(f"/api/repos/{repo.id}/graph", headers=auth).status_code == 409
