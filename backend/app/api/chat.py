"""Chat endpoints — grounded RAG over the repo's indexed code (Phase 1.5)."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import SessionLocal, get_db
from app.models.chat import ChatMessage, ChatRole, ChatSession
from app.models.repo import Repo, RepoStatus
from app.models.user import User
from app.schemas.chat import ChatMessageOut, ChatRequest, ChatResponse
from app.services import llm
from app.services.vectorstore import VectorStore

router = APIRouter()

TOP_K = 6


def _owned_ready_repo(repo_id: str, user: User, db: Session) -> Repo:
    repo = db.get(Repo, repo_id)
    if repo is None or repo.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repo not found")
    if repo.status != RepoStatus.ready or not repo.chroma_collection:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Repo is not indexed yet (status: {repo.status.value})",
        )
    return repo


def _get_or_create_session(repo: Repo, db: Session) -> ChatSession:
    session = db.scalar(
        select(ChatSession)
        .where(ChatSession.repo_id == repo.id)
        .order_by(ChatSession.created_at.desc())
    )
    if session is None:
        session = ChatSession(repo_id=repo.id, title="Session 1")
        db.add(session)
        db.commit()
        db.refresh(session)
    return session


def _retrieve(repo: Repo, message: str) -> tuple[list[tuple[str, str]], list[str]]:
    """Return (context_blocks, cited_files) for a question."""
    # chroma_collection is guaranteed non-null by _owned_ready_repo.
    store = VectorStore(repo.chroma_collection or "")
    hits = store.query(message, k=TOP_K)
    context_blocks = [(h.path, h.content) for h in hits]
    cited: list[str] = []
    for h in hits:  # de-dupe paths, preserve rank order
        if h.path not in cited:
            cited.append(h.path)
    return context_blocks, cited


def _persist(
    db: Session,
    session_id: str,
    message: str,
    answer: str,
    files: list[str],
    usage: dict | None,
) -> None:
    """Persist the user + assistant turn on the given session."""
    db.add(ChatMessage(session_id=session_id, role=ChatRole.user, content=message, files=[]))
    db.add(
        ChatMessage(
            session_id=session_id,
            role=ChatRole.assistant,
            content=answer,
            files=files,
            usage=usage,
        )
    )
    db.commit()


@router.post("/{repo_id}/chat", response_model=ChatResponse)
async def chat(
    repo_id: str,
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    repo = _owned_ready_repo(repo_id, user, db)
    session = _get_or_create_session(repo, db)
    context_blocks, cited = _retrieve(repo, body.message)

    result = await llm.complete(body.message, context_blocks)
    answer = result["answer"]
    _persist(db, session.id, body.message, answer, cited, result.get("usage"))
    return ChatResponse(answer=answer, files=cited)


@router.post("/{repo_id}/chat/stream")
async def chat_stream(
    repo_id: str,
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """SSE token stream. Emits a `sources` event, then `token` events, then `done`."""
    repo = _owned_ready_repo(repo_id, user, db)
    session = _get_or_create_session(repo, db)
    context_blocks, cited = _retrieve(repo, body.message)

    async def event_gen() -> AsyncIterator[str]:
        yield f"event: sources\ndata: {json.dumps({'files': cited})}\n\n"
        collected: list[str] = []
        async for chunk in llm.stream(body.message, context_blocks):
            collected.append(chunk)
            yield f"event: token\ndata: {json.dumps({'text': chunk})}\n\n"
        answer = "".join(collected)
        # The request-scoped session is closed once streaming begins, so persist
        # the turn on a fresh session owned by the generator.
        stream_db = SessionLocal()
        try:
            _persist(stream_db, session.id, body.message, answer, cited, None)
        finally:
            stream_db.close()
        yield f"event: done\ndata: {json.dumps({'files': cited})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{repo_id}/chat/history", response_model=list[ChatMessageOut])
def chat_history(
    repo_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ChatMessage]:
    repo = db.get(Repo, repo_id)
    if repo is None or repo.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repo not found")
    session = db.scalar(
        select(ChatSession)
        .where(ChatSession.repo_id == repo.id)
        .order_by(ChatSession.created_at.desc())
    )
    if session is None:
        return []
    return list(session.messages)
