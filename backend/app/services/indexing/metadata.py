"""Framework detection, entry points, key files, and health scoring."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.services.indexing.walk import WalkResult

# Marker file -> (framework, dependency substrings that confirm it).
_PY_FRAMEWORKS = [
    ("FastAPI", ("fastapi",)),
    ("Django", ("django",)),
    ("Flask", ("flask",)),
]
_JS_FRAMEWORKS = [
    ("Next.js", ("next",)),
    ("React", ("react",)),
    ("Vue", ("vue",)),
    ("Svelte", ("svelte",)),
    ("Express", ("express",)),
    ("NestJS", ("@nestjs/core",)),
]

ENTRY_CANDIDATES = (
    "main.py", "app.py", "manage.py", "wsgi.py", "asgi.py",
    "index.ts", "index.js", "main.ts", "main.tsx", "main.go",
    "server.ts", "server.js", "Main.java", "cmd/main.go",
)
KEY_FILE_NAMES = (
    "package.json", "pyproject.toml", "requirements.txt", "go.mod", "pom.xml",
    "build.gradle", "cargo.toml", "dockerfile", "docker-compose.yml",
    "readme.md", "vite.config.ts", "next.config.js", "tsconfig.json",
    ".env.example", "makefile",
)


@dataclass
class RepoMetadata:
    primary_language: str | None
    framework: str
    entry_points: list[str]
    key_files: list[str]
    health_score: int


def _detect_framework(root: Path, walk: WalkResult) -> str:
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8", errors="ignore"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            dep_keys = " ".join(deps.keys()).lower()
            for fw, markers in _JS_FRAMEWORKS:
                if any(m in dep_keys for m in markers):
                    return fw
        except (json.JSONDecodeError, OSError):
            pass
        return "Node.js"

    for marker in ("pyproject.toml", "requirements.txt", "setup.py", "pipfile"):
        p = root / marker
        if p.exists():
            blob = p.read_text(encoding="utf-8", errors="ignore").lower()
            for fw, markers in _PY_FRAMEWORKS:
                if any(m in blob for m in markers):
                    return fw
            return "Python"

    if (root / "go.mod").exists():
        blob = (root / "go.mod").read_text(encoding="utf-8", errors="ignore").lower()
        if "gin-gonic" in blob:
            return "Gin"
        if "fiber" in blob:
            return "Fiber"
        return "Go"
    if (root / "pom.xml").exists() or (root / "build.gradle").exists():
        return "Spring Boot" if "springframework" in _read(root / "pom.xml").lower() else "Java"
    if (root / "cargo.toml").exists():
        return "Rust"
    return "—"


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _find_entry_points(walk: WalkResult) -> list[str]:
    found = []
    for f in walk.files:
        base = f.rel_path.split("/")[-1].lower()
        if base in {c.lower() for c in ENTRY_CANDIDATES}:
            found.append(f.rel_path)
    return sorted(found, key=len)[:6]


def _find_key_files(walk: WalkResult) -> list[str]:
    found = []
    for f in walk.files:
        base = f.rel_path.split("/")[-1].lower()
        if base in KEY_FILE_NAMES and "/" not in f.rel_path.strip("/").replace(base, ""):
            found.append(f.rel_path)
    # Prefer root-level config files.
    return sorted(set(found), key=lambda p: (p.count("/"), len(p)))[:10]


def _health_score(root: Path, walk: WalkResult) -> int:
    """Heuristic 0-100: README + tests + lockfile + CI + organisation."""
    names = {f.rel_path.lower() for f in walk.files}
    paths = " ".join(names)
    test_markers = ("test/", "tests/", "spec/", "__tests__", ".test.", "_test.")
    lockfiles = ("package-lock.json", "poetry.lock", "yarn.lock", "go.sum", "pnpm-lock.yaml")
    ci_markers = ("jenkinsfile", ".gitlab-ci.yml", ".circleci/config.yml")
    score = 30  # base
    if any("readme" in n for n in names):
        score += 20
    if any(seg in paths for seg in test_markers):
        score += 20
    if any(n.endswith(lockfiles) for n in names):
        score += 15
    if any(".github/workflows" in n or n in ci_markers for n in names):
        score += 15
    return min(score, 100)


def extract_metadata(root: Path, walk: WalkResult) -> RepoMetadata:
    primary = (
        max(walk.language_bytes.items(), key=lambda kv: kv[1])[0]
        if walk.language_bytes
        else None
    )
    return RepoMetadata(
        primary_language=primary,
        framework=_detect_framework(root, walk),
        entry_points=_find_entry_points(walk),
        key_files=_find_key_files(walk),
        health_score=_health_score(root, walk),
    )
