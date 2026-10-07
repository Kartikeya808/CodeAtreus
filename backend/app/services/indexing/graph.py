"""Build a module dependency graph from extracted imports.

Resolves intra-repo imports to file nodes, assigns a layer ``type`` by path
heuristics (controller/service/repo/db/...), and lays nodes out in horizontal
bands so the result matches the frontend's GRAPH_NODES/GRAPH_EDGES shape.
"""
from __future__ import annotations

import re
from pathlib import PurePosixPath

from app.services.indexing.symbols import FileSymbols

# Layer inference by path/name keywords -> node `type` (and UI colour band).
_LAYER_RULES = [
    ("frontend", ("component", "pages/", "views/", ".tsx", ".jsx", "ui/")),
    ("api", ("router", "routes", "api/", "endpoint", "gateway")),
    ("controller", ("controller", "handler", "resource")),
    ("service", ("service", "usecase", "domain", "agent")),
    ("repo", ("repository", "repo", "dao", "store", "entity", "model")),
    ("db", ("database", "migration", "schema", "db/", "sql")),
]
_LAYER_ORDER = ["frontend", "api", "controller", "service", "repo", "db", "module"]
_IDENT_RE = re.compile(r"[^a-z0-9]+")


def _infer_type(path: str) -> str:
    low = path.lower()
    for layer, keys in _LAYER_RULES:
        if any(k in low for k in keys):
            return layer
    return "module"


def _label(path: str) -> str:
    stem = PurePosixPath(path).stem
    parts = _IDENT_RE.sub(" ", stem).split()
    return "".join(p.capitalize() for p in parts) or stem


_CODE_EXTS = (".tsx", ".ts", ".jsx", ".js", ".mjs", ".py", ".go", ".java", ".rb", ".rs")


def _module_key(imp: str) -> str:
    # Normalise an import target to a comparable module token.
    imp = imp.strip().strip("'\"")
    imp = imp.split(" ")[-1]
    return imp.replace("./", "").replace("../", "").strip("/.")


def _target_stem(token: str) -> str:
    """Last module component of an import, extension-stripped and lowercased.

    Handles slash paths (``./dir/service.ts``), dotted Python modules
    (``src.service``) and bare names (``service``) uniformly.
    """
    seg = token.replace("\\", "/").split("/")[-1]
    for ext in _CODE_EXTS:
        if seg.endswith(ext):
            return seg[: -len(ext)].lower()
    return seg.split(".")[-1].lower()


def build_graph(symbols: list[FileSymbols], max_nodes: int = 60) -> dict:
    """Return {nodes:[{id,label,type,x,y}], edges:[[a,b]]}."""
    # Rank files by connectivity (imports emitted) so we keep the busiest ones.
    ranked = sorted(symbols, key=lambda s: len(s.imports), reverse=True)
    selected = [s for s in ranked if s.language][:max_nodes]

    # Index stems -> path for intra-repo import resolution.
    stem_index: dict[str, str] = {}
    for s in selected:
        stem_index[PurePosixPath(s.rel_path).stem.lower()] = s.rel_path

    def _node_id(path: str) -> str:
        return f"n{abs(hash(path)) % 100000}"

    nodes = []
    for s in selected:
        nodes.append(
            {
                "id": _node_id(s.rel_path),
                "label": _label(s.rel_path),
                "type": _infer_type(s.rel_path),
                "path": s.rel_path,
            }
        )

    edges: list[list[str]] = []
    seen: set[tuple[str, str]] = set()
    for s in selected:
        src = _node_id(s.rel_path)
        for imp in s.imports:
            token = _module_key(imp)
            if not token:
                continue
            target_stem = _target_stem(token)
            target_path = stem_index.get(target_stem)
            if target_path and target_path != s.rel_path:
                dst = _node_id(target_path)
                key = (src, dst)
                if key not in seen:
                    seen.add(key)
                    edges.append([src, dst])

    _assign_layout(nodes)
    _refine_with_networkx(nodes, edges)
    return {"nodes": nodes, "edges": edges}


def _assign_layout(nodes: list[dict]) -> None:
    """Lay nodes out in a wrapping grid, grouped by layer.

    Nodes render as 120x44 boxes on the client, so cells are spaced wider than
    that to avoid overlap. A single horizontal band can't hold 50+ same-layer
    nodes legibly, so we flow them left-to-right and wrap onto new rows.
    """
    import math

    col_w, row_h, margin = 160, 85, 20

    def _order(n: dict) -> tuple[int, str]:
        layer = n["type"] if n["type"] in _LAYER_ORDER else "module"
        return _LAYER_ORDER.index(layer), n.get("label", "")

    ordered = sorted(nodes, key=_order)
    count = len(ordered) or 1
    # Aim for a slightly-wide grid that stays readable (never a single long row).
    cols = max(4, min(count, math.ceil(math.sqrt(count * 1.7))))
    for i, n in enumerate(ordered):
        n["x"] = margin + (i % cols) * col_w
        n["y"] = margin + (i // cols) * row_h


def _refine_with_networkx(nodes: list[dict], edges: list[list[str]]) -> None:
    """If NetworkX is present, nudge x within bands using degree centrality."""
    try:
        import networkx as nx
    except Exception:  # noqa: BLE001 - optional
        return
    g = nx.DiGraph()
    g.add_nodes_from(n["id"] for n in nodes)
    g.add_edges_from((a, b) for a, b in edges)
    centrality = nx.degree_centrality(g) if g.number_of_nodes() else {}
    for n in nodes:
        n["degree"] = round(centrality.get(n["id"], 0.0), 3)
