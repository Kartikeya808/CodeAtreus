"""DB-backed cache for grounded chat answers (Phase 4.6).

Keyed by a hash of the repo, its indexed commit sha, and the normalised
question so repeated questions skip the LLM call and the cache invalidates
when the repo is re-indexed at a new commit. DB-backed (not Redis) to stay
within the free single-service deployment.
"""
from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.llm_cache import LLMCache


def make_key(repo_id: str, commit_sha: str | None, question: str) -> str:
    normalised = " ".join(question.lower().split())
    raw = f"{repo_id}:{commit_sha or 'none'}:{normalised}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get(db: Session, key: str) -> LLMCache | None:
    return db.scalar(select(LLMCache).where(LLMCache.cache_key == key))


def put(
    db: Session, repo_id: str, key: str, question: str, answer: str, files: list[str]
) -> None:
    # Ignore if another request cached the same key concurrently.
    if get(db, key) is not None:
        return
    db.add(LLMCache(
        cache_key=key, repo_id=repo_id, question=question, answer=answer, files=files
    ))
    db.commit()
