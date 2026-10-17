"""Decision timeline (Phase 4.1): cluster a repo's commit history and summarise
the "why" of each cluster.

Commits are fetched from the GitHub REST API (authenticated with the owner's
token when available, falling back to unauthenticated for public repos), grouped
into ISO-week clusters, and each cluster is summarised with one LLM call. Every
network/LLM step degrades gracefully so the endpoint never hard-fails.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.core.logging import get_logger
from app.services import llm

logger = get_logger("timeline")

MAX_COMMITS = 100
MAX_CLUSTERS = 12


@dataclass
class Commit:
    sha: str
    message: str
    author: str
    date: str  # ISO-8601


async def fetch_commits(
    full_name: str, token: str | None, limit: int = MAX_COMMITS
) -> list[Commit]:
    """Fetch the most recent commits for ``owner/repo``. [] on any failure."""
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://api.github.com/repos/{full_name}/commits"
    try:
        async with httpx.AsyncClient(timeout=20.0) as http:
            resp = await http.get(url, headers=headers, params={"per_page": min(limit, 100)})
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001 - never let a commit fetch break the endpoint
        logger.info("commit fetch failed for %s: %s", full_name, exc)
        return []

    commits: list[Commit] = []
    for item in data:
        commit = item.get("commit", {})
        author = commit.get("author", {}) or {}
        commits.append(Commit(
            sha=(item.get("sha") or "")[:7],
            message=(commit.get("message") or "").strip(),
            author=author.get("name", "unknown"),
            date=author.get("date", ""),
        ))
    return commits


def _week_key(iso_date: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
    except ValueError:
        return "unknown"
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def cluster_by_week(commits: list[Commit]) -> list[dict]:
    """Group commits into ISO-week buckets, newest first."""
    buckets: dict[str, list[Commit]] = {}
    for c in commits:
        buckets.setdefault(_week_key(c.date), []).append(c)
    ordered = sorted(buckets.items(), key=lambda kv: kv[0], reverse=True)
    clusters: list[dict] = []
    for period, items in ordered[:MAX_CLUSTERS]:
        clusters.append({
            "period": period,
            "commits": [
                {"sha": c.sha, "message": c.message.splitlines()[0][:120],
                 "author": c.author, "date": c.date}
                for c in items
            ],
        })
    return clusters


def _heuristic_summary(commits: list[dict]) -> str:
    subjects = [c["message"] for c in commits[:5]]
    return "Key changes: " + "; ".join(subjects)


async def _summarise(commits: list[dict], api_key: str | None) -> str:
    """One-line "why" summary for a cluster, via LLM when configured."""
    if not llm.llm_configured(api_key):
        return _heuristic_summary(commits)
    messages = "\n".join(f"- {c['message']}" for c in commits[:30])
    question = (
        "Summarise, in one or two sentences, the theme and intent behind this "
        "batch of commits (what was being built or fixed and why)."
    )
    result = await llm.complete(question, [("commits", messages)], api_key=api_key)
    return result["answer"].strip()


def _title(commits: list[dict]) -> str:
    return commits[0]["message"] if commits else "Changes"


async def build_timeline(full_name: str, token: str | None, api_key: str | None) -> dict:
    """Fetch, cluster, and summarise a repo's commit timeline."""
    commits = await fetch_commits(full_name, token)
    clusters = cluster_by_week(commits)
    for cluster in clusters:
        cluster["title"] = _title(cluster["commits"])
        cluster["summary"] = await _summarise(cluster["commits"], api_key)
    return {
        "clusters": clusters,
        "commit_count": len(commits),
        "generated_at": datetime.now(UTC).isoformat(),
    }
