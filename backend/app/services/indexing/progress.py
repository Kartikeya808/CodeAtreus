"""Index-job progress updates + realtime fan-out to WebSocket subscribers."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.index_job import IndexJob, IndexStatus
from app.models.repo import Repo, RepoStatus

logger = get_logger("indexing.progress")


def _publish(repo_id: str, payload: dict) -> None:
    """Best-effort publish of a progress event to Redis pub/sub for WS clients."""
    try:
        import redis  # type: ignore[import-untyped]  # local import: optional dep

        from app.core.config import settings

        client = redis.Redis.from_url(settings.redis_url)
        client.publish(f"indexing:{repo_id}", json.dumps(payload))
        client.close()
    except Exception as exc:  # noqa: BLE001 - realtime is best-effort
        logger.debug("progress publish skipped: %s", exc)


class ProgressReporter:
    """Writes step/label/log updates to the IndexJob row and fans them out."""

    def __init__(self, db: Session, job: IndexJob, repo: Repo):
        self.db = db
        self.job = job
        self.repo = repo

    def start(self) -> None:
        self.job.status = IndexStatus.running
        self.repo.status = RepoStatus.indexing
        self._commit()

    def step(self, step: int, label: str, log: str | None = None) -> None:
        self.job.step = step
        self.job.label = label
        if log:
            self.job.logs = [*(self.job.logs or []), log]
        self._commit()

    def log(self, message: str) -> None:
        self.job.logs = [*(self.job.logs or []), message]
        self._commit()

    def complete(self) -> None:
        self.job.status = IndexStatus.ready
        self.job.step = self.job.total
        self.job.label = "Ready"
        self.repo.status = RepoStatus.ready
        self._commit()

    def fail(self, error: str) -> None:
        self.job.status = IndexStatus.failed
        self.job.error = error[:2048]
        self.job.logs = [*(self.job.logs or []), f"ERROR: {error}"]
        self.repo.status = RepoStatus.failed
        self._commit()

    def _commit(self) -> None:
        self.db.add(self.job)
        self.db.add(self.repo)
        self.db.commit()
        _publish(
            self.repo.id,
            {
                "status": self.job.status.value,
                "step": self.job.step,
                "total": self.job.total,
                "label": self.job.label,
                "logs": self.job.logs,
            },
        )
