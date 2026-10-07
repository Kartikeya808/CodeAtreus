"""Celery tasks. The heavy pipeline lives in app.services.indexing.pipeline."""
from __future__ import annotations

from app.services.indexing.pipeline import run_index_pipeline
from app.worker.celery_app import celery_app


@celery_app.task(name="index_repo", bind=True, max_retries=1)
def index_repo_task(self, repo_id: str, job_id: str) -> str:  # noqa: ANN001
    run_index_pipeline(repo_id, job_id)
    return repo_id
