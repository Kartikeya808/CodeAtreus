"""Schemas for flow, sequence, search, and api-docs endpoints."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class FlowRequest(BaseModel):
    entrypoint: str | None = None


class FlowStep(BaseModel):
    label: str
    type: str
    detail: str


class FlowOut(BaseModel):
    steps: list[FlowStep]


class SequenceOut(BaseModel):
    mermaid: str
    plantuml: str


class SearchResult(BaseModel):
    file: str
    path: str
    line: int
    relevance: int
    snippet: str


class ApiDocsOut(BaseModel):
    openapi: str
    info: dict[str, Any]
    paths: dict[str, Any]
