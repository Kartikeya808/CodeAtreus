"""Phase 1.3 — end-to-end pipeline against a real local git repo (no network).

Clones from a file:// path so the full pipeline (clone → walk → symbols →
metadata → embed → graph → overview) runs with no GitHub dependency.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from app.models.index_job import IndexJob, IndexStatus
from app.models.repo import Repo, RepoStatus
from app.models.user import User
from app.services.indexing.clone import clone_repo
from app.services.indexing.pipeline import run_index_pipeline


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """A minimal Python+TS repo committed on branch main."""
    src = tmp_path / "sample"
    (src / "src").mkdir(parents=True)
    (src / "README.md").write_text("# Sample\nDemo repo for indexing tests.\n")
    (src / "requirements.txt").write_text("fastapi\nuvicorn\n")
    (src / "src" / "main.py").write_text(
        "from src.service import run\n\n"
        "def main():\n    return run()\n"
    )
    (src / "src" / "service.py").write_text(
        "class Service:\n    def run(self):\n        return 42\n\n"
        "def run():\n    return Service().run()\n"
    )
    (src / "tests").mkdir()
    (src / "tests" / "test_x.py").write_text("def test_ok():\n    assert True\n")

    _git(["init", "-b", "main"], src)
    _git(["config", "user.email", "t@t.co"], src)
    _git(["config", "user.name", "t"], src)
    _git(["add", "."], src)
    _git(["commit", "-m", "init"], src)
    return src


def test_full_pipeline(db_session, tmp_path, sample_repo, monkeypatch):
    # Clone into an isolated dir under tmp.
    monkeypatch.setenv("CLONE_DIR", str(tmp_path / "clones"))
    monkeypatch.setattr(
        "app.services.indexing.clone.settings.clone_dir", str(tmp_path / "clones")
    )
    monkeypatch.setattr(
        "app.services.vectorstore.settings.chroma_persist_dir", str(tmp_path / "chroma")
    )

    user = User(github_login="dev")
    db_session.add(user)
    db_session.commit()

    repo = Repo(
        owner_id=user.id,
        github_url=f"file://{sample_repo}",
        full_name="local/sample",
        name="sample",
        default_branch="main",
    )
    db_session.add(repo)
    db_session.flush()
    job = IndexJob(repo_id=repo.id)
    db_session.add(job)
    db_session.commit()

    # The pipeline opens its own session; point SessionLocal at the test engine.
    import app.services.indexing.pipeline as pipe
    monkeypatch.setattr(pipe, "SessionLocal", lambda: _BoundSession(db_session))

    run_index_pipeline(repo.id, job.id)

    db_session.refresh(repo)
    db_session.refresh(job)

    assert repo.status == RepoStatus.ready
    assert job.status == IndexStatus.ready
    assert job.step == 7
    assert repo.framework == "FastAPI"
    assert repo.primary_language == "Python"
    assert repo.health_score >= 70  # README + tests + base
    assert repo.file_count >= 4

    ov = repo.overview
    assert any(s["name"] == "Python" for s in ov["language_dist"])
    assert any("readme" in k.lower() for k in ov["key_files"])
    assert "src/main.py" in ov["entry_points"]

    # Dependency graph resolved the intra-repo import main -> service.
    labels = {n["label"] for n in repo.graph["nodes"]}
    assert "Main" in labels and "Service" in labels
    assert repo.graph["edges"]


def test_clone_falls_back_on_wrong_default_branch(tmp_path, monkeypatch):
    """A repo on `master` must still clone when we wrongly request `main`.

    Reproduces the GitHub-API-unavailable case where default_branch defaults to
    "main" but the repo actually uses "master".
    """
    src = tmp_path / "masterrepo"
    src.mkdir()
    (src / "readme.md").write_text("# master repo\n")
    _git(["init", "-b", "master"], src)
    _git(["config", "user.email", "t@t.co"], src)
    _git(["config", "user.name", "t"], src)
    _git(["add", "."], src)
    _git(["commit", "-m", "init"], src)

    monkeypatch.setattr("app.services.indexing.clone.settings.clone_dir", str(tmp_path / "clones"))

    # Request the wrong branch; clone_repo should retry the remote default.
    dest = clone_repo(f"file://{src}", "main", "repo123")
    assert dest.exists()
    assert (dest / "readme.md").exists()


class _BoundSession:
    """Wrap the test session so pipeline's `db.close()` doesn't drop it."""

    def __init__(self, session):
        self._s = session

    def __getattr__(self, item):
        return getattr(self._s, item)

    def close(self):  # pipeline closes its session in `finally`
        pass
