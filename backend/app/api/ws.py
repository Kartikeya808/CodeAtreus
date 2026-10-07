"""WebSocket endpoint streaming indexing progress: /ws/indexing/{repo_id}.

Subscribes to the Redis channel the pipeline publishes to. When Redis is
unavailable it falls back to polling the IndexJob row, so the progress bar still
advances in a single-process local run.
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.index_job import IndexJob, IndexStatus
from app.models.repo import Repo

logger = get_logger("ws.indexing")
ws_router = APIRouter()

_TERMINAL = {IndexStatus.ready.value, IndexStatus.failed.value}


def _latest_status(repo_id: str) -> dict | None:
    db = SessionLocal()
    try:
        repo = db.get(Repo, repo_id)
        if repo is None:
            return None
        job = (
            db.query(IndexJob)
            .filter(IndexJob.repo_id == repo_id)
            .order_by(IndexJob.created_at.desc())
            .first()
        )
        if job is None:
            return None
        return {
            "status": job.status.value,
            "step": job.step,
            "total": job.total,
            "label": job.label,
            "logs": job.logs or [],
        }
    finally:
        db.close()


@ws_router.websocket("/ws/indexing/{repo_id}")
async def indexing_ws(websocket: WebSocket, repo_id: str) -> None:
    await websocket.accept()

    # Send the current snapshot immediately.
    snapshot = _latest_status(repo_id)
    if snapshot is None:
        await websocket.send_json({"error": "repo not found"})
        await websocket.close()
        return
    await websocket.send_json(snapshot)
    if snapshot["status"] in _TERMINAL:
        await websocket.close()
        return

    try:
        await _stream_redis(websocket, repo_id)
    except Exception as exc:  # noqa: BLE001 - fall back to polling
        logger.info("redis stream unavailable (%s); polling", exc)
        await _stream_polling(websocket, repo_id)


async def _stream_redis(websocket: WebSocket, repo_id: str) -> None:
    import redis.asyncio as aioredis  # type: ignore[import-untyped]

    client = aioredis.from_url(settings.redis_url)
    pubsub = client.pubsub()
    await pubsub.subscribe(f"indexing:{repo_id}")
    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            payload = json.loads(message["data"])
            await websocket.send_json(payload)
            if payload.get("status") in _TERMINAL:
                break
    finally:
        await pubsub.close()
        await client.close()
    await websocket.close()


async def _stream_polling(websocket: WebSocket, repo_id: str) -> None:
    last: dict | None = None
    try:
        while True:
            snapshot = _latest_status(repo_id)
            if snapshot and snapshot != last:
                await websocket.send_json(snapshot)
                last = snapshot
                if snapshot["status"] in _TERMINAL:
                    break
            await asyncio.sleep(0.8)
    except WebSocketDisconnect:
        return
    await websocket.close()
