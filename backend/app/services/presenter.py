"""Formatting helpers that shape ORM rows into the frontend's expected JSON."""
from __future__ import annotations

from datetime import UTC, datetime

from app.models.repo import Repo

# Language -> accent colour, matching the palette used across the UI.
LANGUAGE_COLORS: dict[str, str] = {
    "TypeScript": "#3b82f6",
    "JavaScript": "#eab308",
    "Python": "#10b981",
    "Java": "#f59e0b",
    "Go": "#ef4444",
    "Rust": "#f97316",
    "Ruby": "#dc2626",
    "C++": "#8b5cf6",
    "C": "#6b7280",
    "C#": "#22c55e",
    "PHP": "#6366f1",
    "Kotlin": "#a855f7",
    "Swift": "#fb923c",
}
DEFAULT_COLOR = "#8b5cf6"


def language_color(language: str | None) -> str:
    return LANGUAGE_COLORS.get(language or "", DEFAULT_COLOR)


def humanize_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} GB"


def relative_time(dt: datetime | None) -> str:
    if dt is None:
        return "never"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    delta = datetime.now(UTC) - dt
    secs = int(delta.total_seconds())
    if secs < 60:
        return "just now"
    mins = secs // 60
    if mins < 60:
        return f"{mins}m ago"
    hours = mins // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 30:
        return f"{days}d ago"
    return f"{days // 30}mo ago"


def repo_to_card(repo: Repo) -> dict[str, object]:
    """Serialise a Repo row into the dashboard/overview card shape."""
    return {
        "id": repo.id,
        "name": repo.name,
        "language": repo.primary_language or "Unknown",
        "framework": repo.framework or "—",
        "stars": repo.stars,
        "lastIndexed": relative_time(repo.updated_at),
        "health": repo.health_score or 0,
        "description": repo.description or "",
        "color": language_color(repo.primary_language),
        "files": repo.file_count,
        "size": humanize_size(repo.size_bytes),
        "status": repo.status,
    }
