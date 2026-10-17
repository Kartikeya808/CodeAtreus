"""Token-usage + activity aggregation over a user's repos and chat history.

Shared by the dashboard stats endpoint and the settings → usage page so the two
never drift. Token counts are summed best-effort from ``ChatMessage.usage`` JSON.
"""
from __future__ import annotations

from collections import OrderedDict
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chat import ChatMessage, ChatRole, ChatSession
from app.models.repo import Repo, RepoStatus

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _month_key(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return f"{dt.year}-{dt.month:02d}"


def _message_tokens(m: ChatMessage) -> int:
    if m.usage and isinstance(m.usage, dict):
        return int(m.usage.get("total_tokens", 0) or 0)
    return 0


def _user_messages(db: Session, user_id: str, role: ChatRole) -> list[ChatMessage]:
    return list(
        db.scalars(
            select(ChatMessage)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .join(Repo, ChatSession.repo_id == Repo.id)
            .where(Repo.owner_id == user_id, ChatMessage.role == role)
        ).all()
    )


def repos_indexed(db: Session, user_id: str) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Repo)
        .where(Repo.owner_id == user_id, Repo.status == RepoStatus.ready)
    ) or 0


def questions_asked(db: Session, user_id: str) -> int:
    return len(_user_messages(db, user_id, ChatRole.user))


def tokens_used(db: Session, user_id: str) -> int:
    return sum(_message_tokens(m) for m in _user_messages(db, user_id, ChatRole.assistant))


def tokens_used_this_month(db: Session, user_id: str) -> int:
    key = _month_key(datetime.now(UTC))
    return sum(
        _message_tokens(m)
        for m in _user_messages(db, user_id, ChatRole.assistant)
        if _month_key(m.created_at) == key
    )


def token_budget(plan: str) -> int:
    """Monthly token budget for a plan. 0 = unlimited."""
    return (
        settings.pro_monthly_token_budget
        if plan == "pro"
        else settings.free_monthly_token_budget
    )


def monthly_series(db: Session, user_id: str, months: int = 6) -> list[dict]:
    """Trailing N-month series of {month, questions, tokens}."""
    now = datetime.now(UTC)
    buckets: OrderedDict[str, dict] = OrderedDict()
    cursor = now.replace(day=1)
    window: list[datetime] = []
    for _ in range(months):
        window.append(cursor)
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    for dt in reversed(window):
        buckets[f"{dt.year}-{dt.month:02d}"] = {
            "month": _MONTHS[dt.month - 1],
            "questions": 0,
            "tokens": 0,
        }

    for m in _user_messages(db, user_id, ChatRole.user):
        key = _month_key(m.created_at)
        if key in buckets:
            buckets[key]["questions"] += 1
    for m in _user_messages(db, user_id, ChatRole.assistant):
        key = _month_key(m.created_at)
        if key in buckets:
            buckets[key]["tokens"] += _message_tokens(m)

    return list(buckets.values())
