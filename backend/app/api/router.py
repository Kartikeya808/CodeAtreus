"""Aggregate API router mounted under the configured prefix (default /api).

Feature routers are added here as each Phase lands. Phase 0 ships health only.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api import analysis, auth, chat, dashboard, explore, health, repos

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(repos.router, prefix="/repos", tags=["repos"])
api_router.include_router(chat.router, prefix="/repos", tags=["chat"])
api_router.include_router(analysis.router, prefix="/repos", tags=["analysis"])
api_router.include_router(explore.router, prefix="/repos", tags=["explore"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
