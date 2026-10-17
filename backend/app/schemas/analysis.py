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


# ── Security (Phase 4.2) ───────────────────────────────────────────────────────
class SecretFinding(BaseModel):
    file: str
    line: int
    rule: str
    severity: str
    preview: str


class Vulnerability(BaseModel):
    package: str
    version: str
    ecosystem: str
    id: str
    severity: str
    summary: str
    fixed_in: str | None = None


class SecurityOut(BaseModel):
    secrets: list[SecretFinding]
    vulnerabilities: list[Vulnerability]
    dependencies_scanned: int
    scanned_at: str


# ── Dead code + drift (Phases 4.3, 4.4) ────────────────────────────────────────
class DeadCodeItem(BaseModel):
    file: str
    symbol: str
    kind: str
    confidence: str


class DriftOut(BaseModel):
    # Each violation is {from, to, from_layer, to_layer, rule}; passed through
    # raw so the `from` key (a Python keyword) survives to the client.
    violations: list[dict]
    score: int
    edges_checked: int


# ── Timeline (Phase 4.1) ────────────────────────────────────────────────────────
class TimelineCommit(BaseModel):
    sha: str
    message: str
    author: str
    date: str


class TimelineCluster(BaseModel):
    period: str
    title: str
    summary: str
    commits: list[TimelineCommit]


class TimelineOut(BaseModel):
    clusters: list[TimelineCluster]
    commit_count: int
    generated_at: str


# ── Dashboard ─────────────────────────────────────────────────────────────────
class DashboardStats(BaseModel):
    repos_indexed: int
    questions_asked: int
    tokens_used: int


class ActivityPoint(BaseModel):
    date: str
    repos: int
    questions: int
