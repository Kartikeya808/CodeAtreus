"""Repository import + management endpoints (Phase 1.2)."""
from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.index_job import TOTAL_STEPS, IndexJob, IndexStatus
from app.models.repo import Repo, RepoStatus
from app.models.user import User
from app.schemas.indexing import IndexStatusOut, OverviewOut
from app.schemas.repo import RepoImportRequest, RepoImportResponse, RepoOut
from app.services import crypto
from app.services.github_repo import InvalidRepoURL, fetch_repo_meta, validate_github_url
from app.services.indexing import enqueue_indexing
from app.services.indexing.clone import remote_head_sha
from app.services.presenter import repo_to_card
from app.services.vectorstore import VectorStore

logger = get_logger("api.repos")

router = APIRouter()


def _get_owned_repo(repo_id: str, user: User, db: Session) -> Repo:
    repo = db.get(Repo, repo_id)
    if repo is None or repo.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repo not found")
    return repo


def teardown_repo_artifacts(repo: Repo) -> None:
    """Drop a repo's index artifacts: vector collection + local clone on disk.

    Best-effort — logs and continues on failure so a partial teardown never
    blocks deleting the DB row. Does not commit; the caller owns the session.
    """
    if repo.chroma_collection:
        try:
            VectorStore(repo.chroma_collection).delete()
        except Exception as exc:  # noqa: BLE001
            logger.info("vector store teardown failed for %s: %s", repo.id, exc)
    if repo.local_path:
        try:
            shutil.rmtree(Path(repo.local_path).expanduser(), ignore_errors=True)
        except OSError as exc:
            logger.info("clone dir teardown failed for %s: %s", repo.id, exc)


@router.post("/import", response_model=RepoImportResponse, status_code=status.HTTP_202_ACCEPTED)
async def import_repo(
    body: RepoImportRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RepoImportResponse:
    """Validate a GitHub URL, create the repo + index job, and kick off indexing."""
    try:
        ref = validate_github_url(body.github_url)
    except InvalidRepoURL as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    # Idempotency: re-importing the same repo re-indexes the existing row.
    repo = db.scalar(
        select(Repo).where(Repo.owner_id == user.id, Repo.full_name == ref.full_name)
    )
    try:
        meta = await fetch_repo_meta(ref, token=crypto.decrypt(user.github_access_token))
    except InvalidRepoURL as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if repo is None:
        repo = Repo(
            owner_id=user.id,
            github_url=ref.clone_url,
            full_name=ref.full_name,
            name=ref.repo,
        )
        db.add(repo)
    repo.default_branch = meta.default_branch
    repo.description = meta.description
    repo.stars = meta.stars

    # Incremental re-index skip (Phase 4.6): if the repo is already indexed at
    # the current remote HEAD, there's nothing to re-embed — return as-is.
    if repo.status == RepoStatus.ready and repo.indexed_commit_sha:
        remote_sha = remote_head_sha(ref.clone_url, meta.default_branch)
        if remote_sha and remote_sha == repo.indexed_commit_sha:
            db.commit()
            db.refresh(repo)
            return RepoImportResponse(repo_id=repo.id, status=repo.status, job_id=None)

    repo.status = RepoStatus.queued

    job = IndexJob(repo=repo, status=IndexStatus.queued, label="Queued")
    db.add(job)
    db.commit()
    db.refresh(repo)
    db.refresh(job)

    enqueue_indexing(repo.id, job.id)
    return RepoImportResponse(repo_id=repo.id, status=repo.status, job_id=job.id)


@router.get("", response_model=list[RepoOut])
def list_repos(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict[str, object]]:
    repos = db.scalars(
        select(Repo).where(Repo.owner_id == user.id).order_by(Repo.updated_at.desc())
    ).all()
    return [repo_to_card(r) for r in repos]


@router.get("/{repo_id}", response_model=RepoOut)
def get_repo(
    repo_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict[str, object]:
    return repo_to_card(_get_owned_repo(repo_id, user, db))


@router.get("/{repo_id}/status", response_model=IndexStatusOut)
def repo_status(
    repo_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> IndexStatusOut:
    """Latest indexing-job status — polled by the `indexing` page (also via WS)."""
    repo = _get_owned_repo(repo_id, user, db)
    job = db.scalar(
        select(IndexJob)
        .where(IndexJob.repo_id == repo.id)
        .order_by(IndexJob.created_at.desc())
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No index job")
    return IndexStatusOut(
        status=job.status,
        step=job.step,
        total=job.total or TOTAL_STEPS,
        label=job.label,
        logs=job.logs or [],
        error=job.error,
    )


@router.get("/{repo_id}/overview", response_model=OverviewOut)
def repo_overview(
    repo_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> OverviewOut:
    """Indexed project overview (Phase 1.4). 409 until indexing has produced data."""
    repo = _get_owned_repo(repo_id, user, db)
    if not repo.overview:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Overview not ready (repo status: {repo.status.value})",
        )
    ov = repo.overview
    return OverviewOut(
        language_dist=ov.get("language_dist", []),
        framework=ov.get("framework", "—"),
        file_count=ov.get("file_count", 0),
        size=ov.get("size", "0 B"),
        health=ov.get("health", 0),
        entry_points=ov.get("entry_points", []),
        key_files=ov.get("key_files", []),
    )


@router.delete("/{repo_id}/index", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_repo_index(
    repo_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    """Drop the repo's index (embeddings + graph + clone) but keep the row.

    Leaves the repo in ``queued`` so the UI shows it needs re-indexing; a fresh
    import of the same URL re-runs the pipeline.
    """
    repo = _get_owned_repo(repo_id, user, db)
    teardown_repo_artifacts(repo)
    repo.overview = None
    repo.graph = None
    repo.architecture = None
    repo.chroma_collection = None
    repo.local_path = None
    repo.health_score = None
    repo.status = RepoStatus.queued
    db.add(repo)
    db.commit()


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_repo(
    repo_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    repo = _get_owned_repo(repo_id, user, db)
    teardown_repo_artifacts(repo)
    db.delete(repo)
    db.commit()
