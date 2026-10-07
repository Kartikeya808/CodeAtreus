"""Dispatch an indexing job.

Prefers Celery (the production path). If the broker can't be reached — e.g. a
single-process local run without Redis — it falls back to a daemon thread so the
pipeline still executes. Both paths call the same ``run_index_pipeline``.
"""
from __future__ import annotations

import threading

from app.core.logging import get_logger

logger = get_logger("indexing.dispatch")


def _run_in_thread(repo_id: str, job_id: str) -> None:
    from app.services.indexing.pipeline import run_index_pipeline

    thread = threading.Thread(
        target=run_index_pipeline, args=(repo_id, job_id), daemon=True
    )
    thread.start()


def enqueue_indexing(repo_id: str, job_id: str) -> str | None:
    """Queue indexing for a repo. Returns the Celery task id when available."""
    try:
        from app.worker.tasks import index_repo_task

        async_result = index_repo_task.delay(repo_id, job_id)
        logger.info("dispatched celery index task %s", async_result.id)
        return async_result.id
    except Exception as exc:  # noqa: BLE001 - broker down / celery absent
        logger.info("celery unavailable (%s); running indexing in-process", exc)
        _run_in_thread(repo_id, job_id)
        return None
