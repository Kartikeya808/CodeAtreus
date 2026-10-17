"""Shallow git clone with size/time guardrails."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("indexing.clone")


class CloneError(RuntimeError):
    pass


def clone_repo(clone_url: str, branch: str, repo_id: str) -> Path:
    """Shallow-clone ``clone_url`` into the configured clone dir.

    Uses ``--depth 1`` and a hard timeout. The destination is wiped first so
    re-indexing always starts from a clean tree.
    """
    dest = Path(settings.clone_dir).expanduser().resolve() / repo_id
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "git", "clone", "--depth", "1", "--single-branch",
        "--branch", branch, clone_url, str(dest),
    ]
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}  # never hang on credentials
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=settings.clone_timeout_seconds,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(dest, ignore_errors=True)
        raise CloneError(
            f"clone timed out after {settings.clone_timeout_seconds}s"
        ) from exc

    if proc.returncode != 0:
        # The detected default branch can be wrong (e.g. GitHub API unavailable so
        # we guessed "main" but the repo uses "master"). Retry once letting git
        # pick the remote's real default branch.
        if "Remote branch" in proc.stderr or "not found in upstream" in proc.stderr:
            logger.info("branch %s missing, retrying with remote default", branch)
            shutil.rmtree(dest, ignore_errors=True)
            fallback = ["git", "clone", "--depth", "1", clone_url, str(dest)]
            proc = subprocess.run(fallback, capture_output=True, text=True,
                                  timeout=settings.clone_timeout_seconds, env=env)
        if proc.returncode != 0:
            shutil.rmtree(dest, ignore_errors=True)
            raise CloneError(f"git clone failed: {proc.stderr.strip()[:500]}")

    _enforce_size_limit(dest)
    return dest


def head_commit_sha(path: Path) -> str | None:
    """Return the HEAD commit sha of a local clone, or None on failure."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    return proc.stdout.strip() or None if proc.returncode == 0 else None


def remote_head_sha(clone_url: str, branch: str) -> str | None:
    """Return the remote's HEAD sha for ``branch`` via ``git ls-remote``.

    Used to decide whether a re-import actually needs to re-index. Returns None
    on any failure so the caller falls back to a full re-index.
    """
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        proc = subprocess.run(
            ["git", "ls-remote", clone_url, branch, f"refs/heads/{branch}", "HEAD"],
            capture_output=True, text=True, timeout=20, env=env,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    # First column of the first line is the sha.
    return proc.stdout.split()[0].strip() or None


def _enforce_size_limit(path: Path) -> None:
    max_bytes = settings.max_repo_size_mb * 1024 * 1024
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += (Path(root) / f).stat().st_size
            except OSError:
                continue
        if total > max_bytes:
            shutil.rmtree(path, ignore_errors=True)
            raise CloneError(
                f"repository exceeds {settings.max_repo_size_mb} MB size limit"
            )
