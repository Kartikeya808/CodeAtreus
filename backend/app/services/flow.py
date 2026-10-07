"""Flow tracing + sequence-diagram generation from the dependency graph.

Given an entrypoint, walk the stored dependency graph downstream through the
architectural layers to produce an ordered request→…→response step list, and
render that trace as Mermaid and PlantUML sequence diagrams.
"""
from __future__ import annotations

from collections import deque

from app.models.repo import Repo

# Layer ordering used to linearise a trace top→bottom.
_LAYER_ORDER = ["frontend", "api", "controller", "service", "repo", "db", "module"]
# Map internal node types onto the frontend FLOW_STEPS `type` vocabulary.
_FLOW_TYPE = {
    "frontend": "request",
    "api": "controller",
    "controller": "controller",
    "service": "service",
    "repo": "repo",
    "db": "db",
    "module": "service",
}


def _layer_rank(node: dict) -> int:
    t = node.get("type", "module")
    return _LAYER_ORDER.index(t) if t in _LAYER_ORDER else len(_LAYER_ORDER)


def _find_start(nodes: list[dict], entrypoint: str | None) -> dict | None:
    if not nodes:
        return None
    if entrypoint:
        needle = entrypoint.lower()
        # Prefer a path/label match.
        for n in nodes:
            if needle in n.get("path", "").lower() or needle in n.get("label", "").lower():
                return n
    # Otherwise start from the highest layer (frontend/api/controller) node.
    return sorted(nodes, key=_layer_rank)[0]


def trace_flow(repo: Repo, entrypoint: str | None) -> list[dict]:
    """Return an ordered list of {label, type, detail} steps."""
    graph = repo.graph or {"nodes": [], "edges": []}
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    by_id = {n["id"]: n for n in nodes}
    adjacency: dict[str, list[str]] = {}
    for src, dst in edges:
        adjacency.setdefault(src, []).append(dst)

    start = _find_start(nodes, entrypoint)
    steps: list[dict] = []

    # Incoming request bookend.
    label = entrypoint or (f"Entry: {start['label']}" if start else "Incoming request")
    steps.append(
        {"label": label, "type": "request", "detail": "Incoming request to the application"}
    )

    if start:
        # BFS downstream from the start node, collecting reachable nodes.
        visited: set[str] = set()
        queue: deque[str] = deque([start["id"]])
        reached: list[dict] = []
        while queue:
            nid = queue.popleft()
            if nid in visited:
                continue
            visited.add(nid)
            node = by_id.get(nid)
            if node is not None:
                reached.append(node)
            for nxt in adjacency.get(nid, []):
                if nxt not in visited:
                    queue.append(nxt)

        # Linearise by architectural layer, then by x position.
        for node in sorted(reached, key=lambda n: (_layer_rank(n), n.get("x", 0))):
            steps.append(
                {
                    "label": node["label"],
                    "type": _FLOW_TYPE.get(node.get("type", "module"), "service"),
                    "detail": f"{node.get('type', 'module')} · {node.get('path', '')}",
                }
            )

    # Response bookend.
    steps.append(
        {"label": "Response", "type": "response", "detail": "Result returned to the caller"}
    )
    return steps


def _safe_participant(label: str) -> str:
    """Mermaid/PlantUML-safe participant identifier."""
    ident = "".join(c if c.isalnum() else "_" for c in label).strip("_")
    return ident or "Node"


def to_mermaid(steps: list[dict]) -> str:
    """Render a trace as a Mermaid sequenceDiagram."""
    actors: list[tuple[str, str]] = []  # (ident, label)
    seen: set[str] = set()
    for s in steps:
        if s["type"] in ("request", "response"):
            continue
        ident = _safe_participant(s["label"])
        if ident not in seen:
            seen.add(ident)
            actors.append((ident, s["label"]))

    lines = ["sequenceDiagram", "    participant Client"]
    for ident, lbl in actors:
        lines.append(f"    participant {ident} as {lbl}")

    chain = [("Client", "Client")] + actors + [("Client", "Client")]
    request_label = steps[0]["label"] if steps else "request"
    for i in range(len(chain) - 1):
        src = chain[i][0]
        dst = chain[i + 1][0]
        if i == 0:
            lines.append(f"    {src}->>{dst}: {request_label}")
        elif i == len(chain) - 2:
            lines.append(f"    {src}-->>{dst}: response")
        else:
            lines.append(f"    {src}->>{dst}: call")
    return "\n".join(lines)


def to_plantuml(steps: list[dict]) -> str:
    """Render a trace as a PlantUML sequence diagram."""
    actors: list[tuple[str, str]] = []
    seen: set[str] = set()
    for s in steps:
        if s["type"] in ("request", "response"):
            continue
        ident = _safe_participant(s["label"])
        if ident not in seen:
            seen.add(ident)
            actors.append((ident, s["label"]))

    lines = ["@startuml", "actor Client"]
    for ident, lbl in actors:
        lines.append(f'participant "{lbl}" as {ident}')

    chain = [("Client", "Client")] + actors + [("Client", "Client")]
    request_label = steps[0]["label"] if steps else "request"
    for i in range(len(chain) - 1):
        src = chain[i][0]
        dst = chain[i + 1][0]
        if i == 0:
            lines.append(f"{src} -> {dst} : {request_label}")
        elif i == len(chain) - 2:
            lines.append(f"{src} --> {dst} : response")
        else:
            lines.append(f"{src} -> {dst} : call")
    lines.append("@enduml")
    return "\n".join(lines)
