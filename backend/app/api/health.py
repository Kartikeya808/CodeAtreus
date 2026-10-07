"""Health + readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.core.config import settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe — always cheap, no external dependencies."""
    return {"status": "ok", "version": __version__, "environment": settings.environment}


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)) -> dict[str, object]:
    """Readiness probe — verifies the database is reachable."""
    checks: dict[str, str] = {}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 - report any failure to the probe
        checks["database"] = f"error: {exc}"
    ready = all(v == "ok" for v in checks.values())
    return {"ready": ready, "checks": checks}
