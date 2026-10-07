"""Generate an OpenAPI-style spec from static route analysis of the clone.

Scans the cloned source for route declarations across common frameworks
(FastAPI, Flask, Express/NestJS, Next.js API routes). Best-effort and regex
based — intended as a discovery aid, not a validator.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.core.logging import get_logger
from app.models.repo import Repo
from app.services.indexing.walk import walk_repo

logger = get_logger("apidocs")

_HTTP = "get|post|put|patch|delete|options|head"

# (framework, regex capturing method + path) applied per matching file type.
_ROUTE_PATTERNS = [
    # FastAPI / Flask-RESTful style: @app.get("/x") / @router.post("/x")
    ("python", re.compile(rf'@\w+\.({_HTTP})\(\s*["\']([^"\']+)["\']', re.I)),
    # Flask: @app.route("/x", methods=["POST"])
    ("python-flask", re.compile(r'@\w+\.route\(\s*["\']([^"\']+)["\']', re.I)),
    # Express / NestJS: app.get("/x"  / router.post('/x'
    ("js", re.compile(rf'\b\w+\.({_HTTP})\(\s*["\']([^"\']+)["\']', re.I)),
]


def generate_openapi(repo: Repo) -> dict:
    spec: dict = {
        "openapi": "3.0.0",
        "info": {"title": f"{repo.name} API", "version": "1.0.0"},
        "paths": {},
    }
    if not repo.local_path:
        return spec
    root = Path(repo.local_path)
    if not root.exists():
        logger.info("clone missing for %s; returning empty api-docs", repo.full_name)
        return spec

    walk = walk_repo(root)
    for sf in walk.files:
        if sf.language not in ("Python", "JavaScript", "TypeScript"):
            continue
        try:
            text = sf.abs_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        _scan_file(text, sf.rel_path, spec)

    return spec


def _scan_file(text: str, rel_path: str, spec: dict) -> None:
    for kind, pattern in _ROUTE_PATTERNS:
        for m in pattern.finditer(text):
            if kind == "python-flask":
                method, path = "get", m.group(1)
            else:
                method, path = m.group(1).lower(), m.group(2)
            if not path.startswith("/"):
                continue
            entry = spec["paths"].setdefault(path, {})
            entry[method] = {
                "summary": f"{method.upper()} {path}",
                "x-source-file": rel_path,
                "responses": {"200": {"description": "Success"}},
            }
