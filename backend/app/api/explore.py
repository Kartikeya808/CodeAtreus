"""Phase 3 endpoints: flow visualizer, sequence diagrams, search, api-docs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.repo import Repo, RepoStatus
from app.models.user import User
from app.schemas.explore import (
    ApiDocsOut,
    FlowOut,
    FlowRequest,
    SearchResult,
    SequenceOut,
)
from app.services import flow as flow_svc
from app.services.apidocs import generate_openapi
from app.services.search import search_repo

router = APIRouter()


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


@router.post("/{repo_id}/flow", response_model=FlowOut)
def trace_flow(
    repo_id: str,
    body: FlowRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FlowOut:
    repo = _ready_repo(repo_id, user, db)
    return FlowOut(steps=flow_svc.trace_flow(repo, body.entrypoint))


@router.post("/{repo_id}/sequence", response_model=SequenceOut)
def sequence_diagram(
    repo_id: str,
    body: FlowRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SequenceOut:
    repo = _ready_repo(repo_id, user, db)
    steps = flow_svc.trace_flow(repo, body.entrypoint)
    return SequenceOut(
        mermaid=flow_svc.to_mermaid(steps),
        plantuml=flow_svc.to_plantuml(steps),
    )


@router.get("/{repo_id}/search", response_model=list[SearchResult])
def search(
    repo_id: str,
    q: str = Query(..., min_length=1),
    k: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    repo = _ready_repo(repo_id, user, db)
    return search_repo(repo, q, k=k)


@router.get("/{repo_id}/api-docs", response_model=ApiDocsOut)
def api_docs(
    repo_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    repo = _ready_repo(repo_id, user, db)
    return generate_openapi(repo)
