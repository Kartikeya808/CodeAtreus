"""Phase 2 analysis endpoints: architecture, important files, roadmap, graph."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.repo import Repo, RepoStatus
from app.models.roadmap import Roadmap
from app.models.user import User
from app.schemas.analysis import (
    ArchitectureSummary,
    DeadCodeItem,
    DriftOut,
    GraphOut,
    ImportantFile,
    RoadmapOut,
    SecurityOut,
    TimelineOut,
)
from app.services import analysis, crypto, quality, security, timeline
from app.services.roadmap_agent import generate_roadmap

router = APIRouter()

# Node colours mirror NODE_COLORS in the frontend (src/App.tsx).
NODE_COLORS = {
    "frontend": "#3b82f6",
    "api": "#8b5cf6",
    "controller": "#06b6d4",
    "service": "#10b981",
    "repo": "#f59e0b",
    "db": "#ef4444",
    "module": "#64748b",
}


def _ready_repo(repo_id: str, user: User, db: Session) -> Repo:
    repo = db.get(Repo, repo_id)
    if repo is None or repo.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repo not found")
    if repo.status != RepoStatus.ready:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Repo is not indexed yet (status: {repo.status.value})",
        )
    return repo


@router.post("/{repo_id}/architecture-summary", response_model=ArchitectureSummary)
async def architecture_summary(
    repo_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ArchitectureSummary:
    repo = _ready_repo(repo_id, user, db)
    result = await analysis.architecture_summary(repo)
    if result.get("generated_by") == "llm" and repo.architecture != result:
        repo.architecture = result  # cache generated summary
        db.add(repo)
        db.commit()
    return ArchitectureSummary(**result)


@router.get("/{repo_id}/important-files", response_model=list[ImportantFile])
def important_files(
    repo_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict]:
    repo = _ready_repo(repo_id, user, db)
    return analysis.important_files(repo)


@router.get("/{repo_id}/roadmap", response_model=RoadmapOut)
async def get_roadmap(
    repo_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> RoadmapOut:
    """Return the latest roadmap, generating one lazily on first request."""
    repo = _ready_repo(repo_id, user, db)
    roadmap = db.scalar(
        select(Roadmap).where(Roadmap.repo_id == repo.id).order_by(Roadmap.created_at.desc())
    )
    if roadmap is None:
        days = await generate_roadmap(repo)
        roadmap = Roadmap(repo_id=repo.id, days=days)
        db.add(roadmap)
        db.commit()
        db.refresh(roadmap)
    return RoadmapOut(days=roadmap.days)


@router.post("/{repo_id}/roadmap/generate", response_model=RoadmapOut)
async def regenerate_roadmap(
    repo_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> RoadmapOut:
    repo = _ready_repo(repo_id, user, db)
    days = await generate_roadmap(repo)
    roadmap = Roadmap(repo_id=repo.id, days=days)
    db.add(roadmap)
    db.commit()
    return RoadmapOut(days=days)


@router.get("/{repo_id}/security", response_model=SecurityOut)
async def get_security(
    repo_id: str,
    refresh: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SecurityOut:
    """Secret scan + dependency vulnerabilities. Cached on the repo; pass
    ``?refresh=true`` to re-scan (requires the clone to still be on disk)."""
    repo = _ready_repo(repo_id, user, db)
    if repo.security and not refresh:
        return SecurityOut(**repo.security)
    if not repo.local_path or not Path(repo.local_path).exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repo clone is not available on disk; re-import to scan.",
        )
    result = await security.run_security_scan(Path(repo.local_path))
    repo.security = result
    db.add(repo)
    db.commit()
    return SecurityOut(**result)


@router.get("/{repo_id}/dead-code", response_model=list[DeadCodeItem])
def get_dead_code(
    repo_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict]:
    """Likely-unused symbols + orphan files. Requires the clone on disk."""
    repo = _ready_repo(repo_id, user, db)
    if not repo.local_path or not Path(repo.local_path).exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repo clone is not available on disk; re-import to analyse.",
        )
    return quality.detect_dead_code(Path(repo.local_path), repo.graph)


@router.get("/{repo_id}/drift", response_model=DriftOut)
def get_drift(
    repo_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> DriftOut:
    """Architecture-drift violations from the persisted dependency graph."""
    repo = _ready_repo(repo_id, user, db)
    return DriftOut(**quality.detect_drift(repo.graph))


@router.get("/{repo_id}/timeline", response_model=TimelineOut)
async def get_timeline(
    repo_id: str,
    refresh: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TimelineOut:
    """Commit-history decision timeline. Cached; ``?refresh=true`` rebuilds.

    Independent of indexing — works off the GitHub API, so it does not require
    the repo to be fully indexed, only owned by the caller.
    """
    repo = db.get(Repo, repo_id)
    if repo is None or repo.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repo not found")
    if repo.timeline and not refresh:
        return TimelineOut(**repo.timeline)
    result = await timeline.build_timeline(
        repo.full_name,
        token=crypto.decrypt(user.github_access_token),
        api_key=crypto.decrypt(user.openrouter_api_key),
    )
    repo.timeline = result
    db.add(repo)
    db.commit()
    return TimelineOut(**result)


@router.get("/{repo_id}/graph", response_model=GraphOut)
def get_graph(
    repo_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> GraphOut:
    repo = _ready_repo(repo_id, user, db)
    graph = repo.graph or {"nodes": [], "edges": []}
    return GraphOut(
        nodes=graph.get("nodes", []),
        edges=graph.get("edges", []),
        colors=NODE_COLORS,
    )
