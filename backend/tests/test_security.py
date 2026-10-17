"""Phase 4.2 — security insights: secret scanning + dependency vulnerabilities."""
from __future__ import annotations

import pytest
from app.models.repo import Repo, RepoStatus
from app.models.user import User
from app.services import security
from app.services.security import Package


@pytest.fixture
def auth(client):
    token = client.post("/api/auth/dev-login").json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── secret scanning ───────────────────────────────────────────────────────────
def test_scan_secrets_detects_known_rules(tmp_path):
    (tmp_path / "config.py").write_text(
        'AWS = "AKIAIOSFODNN7EXAMPLE"\n'
        'gh = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"\n'
        'password = "hunter2hunter2"\n'
        "clean = 1\n"
    )
    findings = security.scan_secrets(tmp_path)
    rules = {f["rule"] for f in findings}
    assert "AWS Access Key ID" in rules
    assert "GitHub Token" in rules
    # Previews are masked, never the raw secret.
    assert all(f["preview"] != "AKIAIOSFODNN7EXAMPLE" for f in findings)


def test_scan_secrets_skips_markdown(tmp_path):
    (tmp_path / "README.md").write_text('token = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"\n')
    assert security.scan_secrets(tmp_path) == []


# ── dependency parsing ────────────────────────────────────────────────────────
def test_parse_requirements(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        "# comment\ndjango==3.0.0\nrequests>=2.0\nflask==2.1.1\n"
    )
    pkgs = security.parse_dependencies(tmp_path)
    names = {(p.name, p.version, p.ecosystem) for p in pkgs}
    assert ("django", "3.0.0", "PyPI") in names
    assert ("flask", "2.1.1", "PyPI") in names
    # Non-pinned (>=) requirements are skipped (OSV needs an exact version).
    assert all(p.name != "requests" for p in pkgs)


def test_parse_package_lock_v3(tmp_path):
    (tmp_path / "package-lock.json").write_text(
        '{"packages": {"": {"name": "root"}, "node_modules/lodash": {"version": "4.17.20"}}}'
    )
    pkgs = security.parse_dependencies(tmp_path)
    assert Package("lodash", "4.17.20", "npm") in pkgs


def test_parse_go_mod(tmp_path):
    (tmp_path / "go.mod").write_text(
        "module example.com/x\n\ngo 1.21\n\nrequire (\n\tgithub.com/pkg/errors v0.9.1\n)\n"
    )
    pkgs = security.parse_dependencies(tmp_path)
    assert Package("github.com/pkg/errors", "0.9.1", "Go") in pkgs


# ── vuln query resilience ─────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_query_vulnerabilities_empty_input():
    assert await security.query_vulnerabilities([]) == []


# ── endpoint ──────────────────────────────────────────────────────────────────
@pytest.fixture
def ready_repo_on_disk(client, auth, db_session, tmp_path):
    user = db_session.query(User).first()
    (tmp_path / "app.py").write_text('SECRET = "AKIAIOSFODNN7EXAMPLE"\n')
    (tmp_path / "requirements.txt").write_text("django==3.0.0\n")
    repo = Repo(
        owner_id=user.id,
        github_url="https://github.com/local/sec.git",
        full_name="local/sec",
        name="sec",
        status=RepoStatus.ready,
        local_path=str(tmp_path),
    )
    db_session.add(repo)
    db_session.commit()
    return repo


def test_security_endpoint_scans_and_caches(client, auth, ready_repo_on_disk, monkeypatch):
    # Avoid hitting the network; stub the OSV query.
    async def _no_vulns(packages):
        return [{
            "package": "django", "version": "3.0.0", "ecosystem": "PyPI",
            "id": "GHSA-xxxx", "severity": "high", "summary": "stub", "fixed_in": "3.0.1",
        }]
    monkeypatch.setattr(security, "query_vulnerabilities", _no_vulns)

    resp = client.get(f"/api/repos/{ready_repo_on_disk.id}/security", headers=auth)
    assert resp.status_code == 200
    body = resp.json()
    assert any(s["rule"] == "AWS Access Key ID" for s in body["secrets"])
    assert body["vulnerabilities"][0]["package"] == "django"
    assert body["dependencies_scanned"] == 1

    # Second call is served from cache (stub returns a different shape if re-run,
    # but caching means we still get the same cached payload).
    cached = client.get(f"/api/repos/{ready_repo_on_disk.id}/security", headers=auth)
    assert cached.status_code == 200
    assert cached.json()["scanned_at"] == body["scanned_at"]


def test_security_409_when_no_clone(client, auth, db_session):
    user = db_session.query(User).first()
    repo = Repo(
        owner_id=user.id,
        github_url="https://github.com/local/nodisk.git",
        full_name="local/nodisk",
        name="nodisk",
        status=RepoStatus.ready,
        local_path=None,
    )
    db_session.add(repo)
    db_session.commit()
    assert client.get(f"/api/repos/{repo.id}/security", headers=auth).status_code == 409
