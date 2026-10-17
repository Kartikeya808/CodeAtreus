"""Phases 4.3 + 4.4 — dead code detection and architecture drift."""
from __future__ import annotations

import pytest
from app.models.repo import Repo, RepoStatus
from app.models.user import User
from app.services import quality


@pytest.fixture
def auth(client):
    token = client.post("/api/auth/dev-login").json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── dead code (unit) ──────────────────────────────────────────────────────────
def test_detect_dead_code_flags_unused_symbol(tmp_path):
    (tmp_path / "used.py").write_text("def shared():\n    return 1\n")
    (tmp_path / "caller.py").write_text("from used import shared\nprint(shared())\n")
    (tmp_path / "lonely.py").write_text("def never_called_anywhere():\n    return 2\n")

    findings = quality.detect_dead_code(tmp_path, graph=None)
    dead = {f["symbol"] for f in findings}
    assert "never_called_anywhere" in dead
    # `shared` is referenced from caller.py, so it must not be flagged.
    assert "shared" not in dead


def test_detect_dead_code_orphan_file():
    graph = {
        "nodes": [
            {"id": "a", "label": "A", "type": "service", "path": "src/a.py"},
            {"id": "b", "label": "B", "type": "service", "path": "src/b.py"},
        ],
        "edges": [["a", "b"]],  # a -> b, so `a` is an orphan (no inbound)
    }
    # Pass an empty dir so only the graph-based orphan detection runs.
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        findings = quality.detect_dead_code(Path(d), graph=graph)
    orphans = {f["file"] for f in findings if f["kind"] == "orphan-file"}
    assert "src/a.py" in orphans
    assert "src/b.py" not in orphans


# ── drift (unit) ──────────────────────────────────────────────────────────────
def test_detect_drift_upward_dependency():
    graph = {
        "nodes": [
            {"id": "c", "label": "Ctrl", "type": "controller"},
            {"id": "s", "label": "Svc", "type": "service"},
        ],
        # service -> controller is an upward (illegal) dependency.
        "edges": [["s", "c"]],
    }
    result = quality.detect_drift(graph)
    assert result["edges_checked"] == 1
    assert len(result["violations"]) == 1
    assert result["violations"][0]["rule"] == "upward-dependency"
    assert result["score"] == 0


def test_detect_drift_clean_graph():
    graph = {
        "nodes": [
            {"id": "c", "label": "Ctrl", "type": "controller"},
            {"id": "s", "label": "Svc", "type": "service"},
        ],
        "edges": [["c", "s"]],  # controller -> service is downward (legal)
    }
    result = quality.detect_drift(graph)
    assert result["violations"] == []
    assert result["score"] == 100


def test_detect_drift_empty():
    assert quality.detect_drift(None)["score"] == 100
    assert quality.detect_drift({"nodes": [], "edges": []})["score"] == 100


# ── endpoints ─────────────────────────────────────────────────────────────────
@pytest.fixture
def ready_repo(client, auth, db_session, tmp_path):
    user = db_session.query(User).first()
    (tmp_path / "lonely.py").write_text("def never_used():\n    return 2\n")
    repo = Repo(
        owner_id=user.id,
        github_url="https://github.com/local/q.git",
        full_name="local/q",
        name="q",
        status=RepoStatus.ready,
        local_path=str(tmp_path),
        graph={
            "nodes": [
                {"id": "s", "label": "Svc", "type": "service", "path": "svc.py"},
                {"id": "c", "label": "Ctrl", "type": "controller", "path": "ctrl.py"},
            ],
            "edges": [["s", "c"]],  # upward violation + c is orphan
        },
    )
    db_session.add(repo)
    db_session.commit()
    return repo


def test_dead_code_endpoint(client, auth, ready_repo):
    resp = client.get(f"/api/repos/{ready_repo.id}/dead-code", headers=auth)
    assert resp.status_code == 200
    symbols = {item["symbol"] for item in resp.json()}
    assert "never_used" in symbols


def test_drift_endpoint(client, auth, ready_repo):
    resp = client.get(f"/api/repos/{ready_repo.id}/drift", headers=auth)
    assert resp.status_code == 200
    body = resp.json()
    assert body["violations"][0]["rule"] == "upward-dependency"
    assert body["violations"][0]["from"] == "Svc"


def test_dead_code_409_without_clone(client, auth, db_session):
    user = db_session.query(User).first()
    repo = Repo(
        owner_id=user.id,
        github_url="https://github.com/local/nd.git",
        full_name="local/nd",
        name="nd",
        status=RepoStatus.ready,
        local_path=None,
    )
    db_session.add(repo)
    db_session.commit()
    assert client.get(f"/api/repos/{repo.id}/dead-code", headers=auth).status_code == 409
