"""Architecture summary + important-file classification from indexed data.

Works off the stored overview + dependency graph (no re-reading of source), so
these endpoints are cheap and deterministic, with an optional LLM pass for the
natural-language architecture summary.
"""
from __future__ import annotations

import json
from collections import defaultdict

from app.core.config import settings
from app.core.logging import get_logger
from app.models.repo import Repo

logger = get_logger("analysis")

# Layer -> human description for the deterministic summary + LLM grounding.
_LAYER_DESCRIPTIONS = {
    "frontend": "UI components and pages",
    "api": "HTTP routing / API gateway",
    "controller": "request handlers / controllers",
    "service": "business logic & domain services",
    "repo": "data access (repositories / models)",
    "db": "database schema & migrations",
    "module": "supporting modules",
}

# Rule-based tags for the important-files view.
_CONFIG_MARKERS = (
    "config", "settings", ".env", "vite.config", "next.config",
    "tsconfig", "pyproject", "package.json",
)
_FILE_TAG_RULES = [
    ("config", _CONFIG_MARKERS),
    ("auth", ("auth", "jwt", "oauth", "login", "security", "token", "guard")),
    ("routes", ("router", "routes", "api/", "endpoint", "controller", "handler")),
    ("database", ("database", "db/", "migration", "entity", "model", "schema", "repository")),
    ("entry", ("main.", "index.", "app.", "server.", "manage.py", "wsgi", "asgi")),
    ("ci", (".github/workflows", "dockerfile", "docker-compose", "jenkinsfile", ".gitlab-ci")),
    ("env", (".env", "environment", "config.py")),
]


def _nodes_by_layer(repo: Repo) -> dict[str, list[dict]]:
    buckets: dict[str, list[dict]] = defaultdict(list)
    graph = repo.graph or {"nodes": []}
    for node in graph.get("nodes", []):
        buckets[node.get("type", "module")].append(node)
    return buckets


def _deterministic_summary(repo: Repo) -> dict:
    """Module breakdown derived purely from the dependency graph + metadata."""
    buckets = _nodes_by_layer(repo)
    modules = []
    for layer, nodes in sorted(buckets.items()):
        modules.append(
            {
                "layer": layer,
                "responsibility": _LAYER_DESCRIPTIONS.get(layer, "modules"),
                "files": [n["path"] for n in nodes][:12],
                "count": len(nodes),
            }
        )
    ov = repo.overview or {}
    summary = (
        f"{repo.name} is a {ov.get('framework', 'software')} project "
        f"({ov.get('file_count', 0)} source files, primary language "
        f"{repo.primary_language or 'mixed'}). It is organised into "
        f"{len(modules)} architectural layers: "
        + ", ".join(f"{m['layer']} ({m['count']})" for m in modules)
        + "."
    )
    return {"summary": summary, "modules": modules, "generated_by": "heuristic"}


async def architecture_summary(repo: Repo) -> dict:
    """Return a cached/generated module responsibility breakdown."""
    if repo.architecture:
        return repo.architecture

    base = _deterministic_summary(repo)
    if not settings.openrouter_api_key:
        return base

    # Enrich the summary prose with an LLM, keeping the structured modules.
    from app.services import llm

    grounding = json.dumps(
        {
            "name": repo.name,
            "framework": (repo.overview or {}).get("framework"),
            "modules": base["modules"],
            "key_files": (repo.overview or {}).get("key_files", []),
        }
    )
    prompt = (
        "Given this repository's module breakdown, write a concise 4-6 sentence "
        "architecture overview explaining how the layers collaborate. Be specific."
    )
    try:
        result = await llm.complete(prompt, [("architecture.json", grounding)])
        base["summary"] = result["answer"]
        base["generated_by"] = "llm"
    except Exception as exc:  # noqa: BLE001
        logger.warning("architecture LLM enrichment failed: %s", exc)
    return base


def important_files(repo: Repo) -> list[dict]:
    """Classify the repo's notable files with rule-based tags."""
    ov = repo.overview or {}
    graph = repo.graph or {"nodes": []}

    candidates: dict[str, set[str]] = {}
    pool = set(ov.get("key_files", [])) | set(ov.get("entry_points", []))
    pool |= {n["path"] for n in graph.get("nodes", [])}

    for path in pool:
        low = path.lower()
        tags = {tag for tag, keys in _FILE_TAG_RULES if any(k in low for k in keys)}
        if not tags:
            # Still surface entry points / key files even if untagged.
            if path in set(ov.get("entry_points", [])):
                tags = {"entry"}
            elif path in set(ov.get("key_files", [])):
                tags = {"config"}
        if tags:
            candidates[path] = tags

    results = [
        {"path": path, "tags": sorted(tags)} for path, tags in candidates.items()
    ]
    # Config/entry/auth first, then alphabetical.
    priority = {"entry": 0, "config": 1, "auth": 2, "routes": 3, "database": 4}
    results.sort(key=lambda r: (min((priority.get(t, 9) for t in r["tags"]), default=9), r["path"]))
    return results[:30]
