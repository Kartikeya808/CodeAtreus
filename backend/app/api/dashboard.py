"""Phase 2.5 — dashboard analytics derived from the user's repos + chat history."""
from __future__ import annotations

from collections import OrderedDict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.chat import ChatMessage, ChatRole, ChatSession
from app.models.repo import Repo, RepoStatus
from app.models.user import User
from app.schemas.analysis import ActivityPoint, DashboardStats

router = APIRouter()

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _user_message_query(user_id: str):
    """Base select for this user's `user`-role chat messages."""
    return (
        select(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .join(Repo, ChatSession.repo_id == Repo.id)
        .where(Repo.owner_id == user_id, ChatMessage.role == ChatRole.user)
    )


@router.get("/stats", response_model=DashboardStats)
def stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DashboardStats:
    repos_indexed = db.scalar(
        select(func.count())
        .select_from(Repo)
        .where(Repo.owner_id == user.id, Repo.status == RepoStatus.ready)
    )
    questions_asked = db.scalar(
        select(func.count()).select_from(_user_message_query(user.id).subquery())
    )
    # Token usage lives on assistant messages' `usage` JSON; sum best-effort.
    assistant_msgs = db.scalars(
        select(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .join(Repo, ChatSession.repo_id == Repo.id)
        .where(Repo.owner_id == user.id, ChatMessage.role == ChatRole.assistant)
    ).all()
    tokens_used = 0
    for m in assistant_msgs:
        if m.usage and isinstance(m.usage, dict):
            tokens_used += int(m.usage.get("total_tokens", 0) or 0)

    return DashboardStats(
        repos_indexed=repos_indexed or 0,
        questions_asked=questions_asked or 0,
        tokens_used=tokens_used,
    )


@router.get("/activity", response_model=list[ActivityPoint])
def activity(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ActivityPoint]:
    """Trailing 7-month series of repos imported + questions asked."""
    now = datetime.now(UTC)
    counts: OrderedDict[str, dict[str, int]] = OrderedDict()
    labels: dict[str, str] = {}
    cursor = now.replace(day=1)
    months: list[datetime] = []
    for _ in range(7):
        months.append(cursor)
        # Step back one month.
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    for dt in reversed(months):
        key = f"{dt.year}-{dt.month:02d}"
        counts[key] = {"repos": 0, "questions": 0}
        labels[key] = _MONTHS[dt.month - 1]

    repos = db.scalars(select(Repo).where(Repo.owner_id == user.id)).all()
    for r in repos:
        key = _key(r.created_at)
        if key in counts:
            counts[key]["repos"] += 1

    messages = db.scalars(_user_message_query(user.id)).all()
    for m in messages:
        key = _key(m.created_at)
        if key in counts:
            counts[key]["questions"] += 1

    return [
        ActivityPoint(date=labels[key], repos=c["repos"], questions=c["questions"])
        for key, c in counts.items()
    ]


def _key(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return f"{dt.year}-{dt.month:02d}"
