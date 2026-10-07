"""Schemas for architecture summary, important files, roadmap, graph, dashboard."""
from __future__ import annotations

from pydantic import BaseModel


# ── Architecture ──────────────────────────────────────────────────────────────
class ArchitectureModule(BaseModel):
    layer: str
    responsibility: str
    files: list[str]
    count: int


class ArchitectureSummary(BaseModel):
    summary: str
    modules: list[ArchitectureModule]
    generated_by: str


# ── Important files ───────────────────────────────────────────────────────────
class ImportantFile(BaseModel):
    path: str
    tags: list[str]


# ── Roadmap ───────────────────────────────────────────────────────────────────
class RoadmapDay(BaseModel):
    day: int
    title: str
    tasks: list[str]
    resources: list[str] = []
    complete: int = 0


class RoadmapOut(BaseModel):
    days: list[RoadmapDay]


# ── Graph ─────────────────────────────────────────────────────────────────────
class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    x: float
    y: float


class GraphOut(BaseModel):
    nodes: list[GraphNode]
    edges: list[list[str]]
    colors: dict[str, str]


# ── Dashboard ─────────────────────────────────────────────────────────────────
class DashboardStats(BaseModel):
    repos_indexed: int
    questions_asked: int
    tokens_used: int


class ActivityPoint(BaseModel):
    date: str
    repos: int
    questions: int
