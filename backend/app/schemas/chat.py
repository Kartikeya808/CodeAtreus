"""Chat request/response schemas (match the frontend CHAT_MESSAGES shape)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    files: list[str]


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    content: str
    files: list[str]
    created_at: datetime
