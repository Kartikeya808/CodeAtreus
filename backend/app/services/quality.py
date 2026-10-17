"""Code-quality analysis (Phases 4.3 + 4.4): dead code and architecture drift.

Dead code: re-extract the symbol table from the clone and flag defined symbols
that are never referenced elsewhere, plus source files with no inbound edges in
the dependency graph. Drift: evaluate the persisted dependency graph against a
layering ruleset derived from the indexer's layer ordering.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.services.indexing.graph import _LAYER_ORDER
from app.services.indexing.symbols import extract_symbols
from app.services.indexing.walk import walk_repo

MAX_DEAD = 200

# Languages where static reference analysis is reliable enough to report with
# higher confidence; everything else is flagged "low".
_STATIC_LANGS = {"Go", "Java", "Rust", "C", "C++", "C#"}
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


# ── Dead code ─────────────────────────────────────────────────────────────────
def detect_dead_code(root: Path, graph: dict | None) -> list[dict]:
    """Flag likely-unused symbols and orphan files.

    Heuristic and intentionally conservative: a symbol is "dead" only if its
    name appears in exactly one file (its definition) across the whole repo.
    """
    walk = walk_repo(root)
    symbols = extract_symbols(walk.files)

    # Count identifier occurrences across all files (cheap global reference map).
    usage: dict[str, int] = {}
    file_text: dict[str, set[str]] = {}
    for sf in walk.files:
        try:
            text = sf.abs_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        idents = set(_IDENT_RE.findall(text))
        file_text[sf.rel_path] = idents
        for ident in idents:
            usage[ident] = usage.get(ident, 0) + 1

    findings: list[dict] = []
    for fs in symbols:
        confidence = "medium" if fs.language in _STATIC_LANGS else "low"
        for kind, names in (("function", fs.functions), ("class", fs.classes)):
            for name in set(names):
                # Defined here; referenced in >1 file means it's used elsewhere.
                if usage.get(name, 0) <= 1:
                    findings.append({
                        "file": fs.rel_path,
                        "symbol": name,
                        "kind": kind,
                        "confidence": confidence,
                    })
                    if len(findings) >= MAX_DEAD:
                        return findings

    # Orphan files: present in the graph with no inbound edges.
    if graph:
        inbound: set[str] = {dst for _, dst in graph.get("edges", [])}
        id_to_path = {n["id"]: n.get("path", n.get("label", "")) for n in graph.get("nodes", [])}
        for node in graph.get("nodes", []):
            if node["id"] not in inbound:
                path = id_to_path.get(node["id"], "")
                # Entry points legitimately have no inbound edges — skip common ones.
                base = Path(path).name.lower()
                if base.startswith(("main.", "index.", "app.", "__init__")):
                    continue
                findings.append({
                    "file": path,
                    "symbol": "(whole file)",
                    "kind": "orphan-file",
                    "confidence": "low",
                })
                if len(findings) >= MAX_DEAD:
                    break
    return findings


# ── Architecture drift ────────────────────────────────────────────────────────
def _layer_index(layer: str) -> int:
    try:
        return _LAYER_ORDER.index(layer)
    except ValueError:
        return _LAYER_ORDER.index("module")


# Presentation layer reaching straight into data layers is a skip violation.
_SKIP_PAIRS = {("frontend", "repo"), ("frontend", "db")}


def detect_drift(graph: dict | None) -> dict:
    """Return {violations:[...], score, edges_checked} for the dependency graph.

    Allowed dependency direction is "downward" through the layer order
    (frontend → api → controller → service → repo → db). An edge pointing
    upward (a lower layer importing a higher one) is architecture drift.
    """
    if not graph or not graph.get("edges"):
        return {"violations": [], "score": 100, "edges_checked": 0}

    layer_of = {n["id"]: n.get("type", "module") for n in graph.get("nodes", [])}
    label_of = {n["id"]: n.get("label", n["id"]) for n in graph.get("nodes", [])}

    violations: list[dict] = []
    checked = 0
    for src, dst in graph.get("edges", []):
        src_layer = layer_of.get(src, "module")
        dst_layer = layer_of.get(dst, "module")
        if "module" in (src_layer, dst_layer):
            continue  # unknown layer — can't judge
        checked += 1
        si, di = _layer_index(src_layer), _layer_index(dst_layer)
        rule: str | None = None
        if di < si:
            rule = "upward-dependency"
        elif (src_layer, dst_layer) in _SKIP_PAIRS:
            rule = "layer-skip"
        if rule:
            violations.append({
                "from": label_of.get(src, src),
                "to": label_of.get(dst, dst),
                "from_layer": src_layer,
                "to_layer": dst_layer,
                "rule": rule,
            })

    score = 100 if checked == 0 else round(100 * (1 - len(violations) / checked))
    return {"violations": violations, "score": score, "edges_checked": checked}
