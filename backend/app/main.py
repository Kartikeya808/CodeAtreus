"""CodeAtreus FastAPI application factory."""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app import __version__
from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger, request_id_var

logger = get_logger("app.main")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a correlation id to every request for structured logging."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["x-request-id"] = rid
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("CodeAtreus API starting (env=%s)", settings.environment)
    yield
    logger.info("CodeAtreus API shutting down")


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title="CodeAtreus API",
        version=__version__,
        description="Repository onboarding agentic platform — backend API.",
        docs_url="/docs",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id"],
    )

    # Everything lives under the /api prefix so the frontend has one base URL.
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    # WebSocket routes are mounted at the root (e.g. /ws/indexing/{id}).
    from app.api.ws import ws_router

    app.include_router(ws_router)

    return app


app = create_app()
