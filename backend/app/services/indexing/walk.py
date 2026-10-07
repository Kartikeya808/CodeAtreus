"""Walk a cloned repo: apply ignore rules, collect files, compute language stats."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import settings

# Directories never worth indexing.
IGNORE_DIRS = {
    ".git", "node_modules", "dist", "build", ".next", "out", "target",
    "__pycache__", ".venv", "venv", "env", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", "vendor", ".idea", ".vscode", "coverage", ".cache",
}
# Extensions treated as binary / non-source.
BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".pdf",
    ".zip", ".tar", ".gz", ".woff", ".woff2", ".ttf", ".eot", ".mp4",
    ".mp3", ".wav", ".so", ".dylib", ".dll", ".exe", ".bin", ".lock",
    ".min.js", ".map",
}
# Extension -> language name (aligned with LANGUAGE_COLORS in presenter.py).
EXT_LANGUAGE = {
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript",
    ".py": "Python", ".java": "Java", ".go": "Go", ".rs": "Rust",
    ".rb": "Ruby", ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++",
    ".c": "C", ".h": "C", ".cs": "C#", ".php": "PHP", ".kt": "Kotlin",
    ".swift": "Swift", ".scala": "Scala", ".sh": "Shell",
}


@dataclass
class SourceFile:
    rel_path: str
    abs_path: Path
    language: str | None
    size: int


@dataclass
class WalkResult:
    files: list[SourceFile] = field(default_factory=list)
    total_bytes: int = 0
    # language name -> total bytes of that language
    language_bytes: dict[str, int] = field(default_factory=dict)

    @property
    def file_count(self) -> int:
        return len(self.files)

    def language_distribution(self) -> list[dict[str, object]]:
        """Return [{name, value(%), color}] sorted desc, matching LANG_DIST."""
        from app.services.presenter import language_color

        total = sum(self.language_bytes.values()) or 1
        dist: list[dict[str, object]] = []
        for lang, byts in sorted(
            self.language_bytes.items(), key=lambda kv: kv[1], reverse=True
        ):
            pct = round(byts / total * 100)
            if pct > 0:
                dist.append({"name": lang, "value": pct, "color": language_color(lang)})
        return dist


def walk_repo(root: Path) -> WalkResult:
    result = WalkResult()
    max_file_bytes = settings.max_file_size_kb * 1024

    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if any(part in IGNORE_DIRS for part in path.relative_to(root).parts):
            continue
        suffix = path.suffix.lower()
        name_lower = path.name.lower()
        if suffix in BINARY_EXTS or name_lower.endswith((".min.js", ".lock")):
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > max_file_bytes:
            continue

        language = EXT_LANGUAGE.get(suffix)
        rel = str(path.relative_to(root))
        result.files.append(SourceFile(rel, path, language, size))
        result.total_bytes += size
        if language:
            result.language_bytes[language] = result.language_bytes.get(language, 0) + size

    return result
