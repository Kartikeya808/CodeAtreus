"""Per-repo chunk store with pluggable backends.

Primary backend: ChromaDB with local embeddings (fastembed / BGE-small).
Fallback backend: a persisted keyword index (TF-ish overlap scoring) so chat
and search work without the vector stack installed. Both expose the same API.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("vectorstore")

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]+")


@dataclass
class Chunk:
    id: str
    path: str
    content: str
    start_line: int = 1


@dataclass
class Retrieved:
    path: str
    content: str
    score: float
    start_line: int = 1


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


# ── Keyword fallback backend ─────────────────────────────────────────────────
class _KeywordStore:
    """Disk-persisted bag-of-words index with cosine-ish scoring."""

    def __init__(self, collection: str):
        self.path = Path(settings.chroma_persist_dir).expanduser() / f"kw_{collection}.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, chunks: list[Chunk]) -> None:
        records = [
            {
                "id": c.id,
                "path": c.path,
                "content": c.content,
                "start_line": c.start_line,
                "tf": dict(Counter(_tokenize(c.content))),
            }
            for c in chunks
        ]
        self.path.write_text(json.dumps(records), encoding="utf-8")

    def query(self, text: str, k: int) -> list[Retrieved]:
        if not self.path.exists():
            return []
        records = json.loads(self.path.read_text(encoding="utf-8"))
        q = Counter(_tokenize(text))
        if not q:
            return []
        q_norm = math.sqrt(sum(v * v for v in q.values())) or 1.0
        scored: list[Retrieved] = []
        for r in records:
            tf: dict[str, int] = r["tf"]
            dot = sum(q[t] * tf.get(t, 0) for t in q)
            if dot <= 0:
                continue
            d_norm = math.sqrt(sum(v * v for v in tf.values())) or 1.0
            # Light boost when query terms appear in the file path.
            path_boost = 1.0 + 0.5 * sum(1 for t in q if t in r["path"].lower())
            scored.append(
                Retrieved(
                    path=r["path"],
                    content=r["content"],
                    score=(dot / (q_norm * d_norm)) * path_boost,
                    start_line=r.get("start_line", 1),
                )
            )
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:k]


# ── Chroma backend ───────────────────────────────────────────────────────────
class _ChromaStore:
    def __init__(self, collection: str):
        import chromadb

        from app.services.embeddings import get_embedding_function

        self._client = chromadb.PersistentClient(
            path=str(Path(settings.chroma_persist_dir).expanduser())
        )
        self._collection = self._client.get_or_create_collection(
            name=collection, embedding_function=get_embedding_function()
        )

    def add(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        self._collection.upsert(
            ids=[c.id for c in chunks],
            documents=[c.content for c in chunks],
            metadatas=[{"path": c.path, "start_line": c.start_line} for c in chunks],
        )

    def query(self, text: str, k: int) -> list[Retrieved]:
        res = self._collection.query(query_texts=[text], n_results=k)
        out: list[Retrieved] = []
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]
        for doc, meta, dist in zip(docs, metas, dists, strict=False):
            out.append(
                Retrieved(
                    path=meta.get("path", "?"),
                    content=doc,
                    score=1.0 - float(dist),  # cosine distance -> similarity
                    start_line=int(meta.get("start_line", 1)),
                )
            )
        return out


@dataclass
class VectorStore:
    collection: str
    _backend: object = field(init=False)

    def __post_init__(self) -> None:
        self._backend = self._make_backend()

    def _make_backend(self) -> object:
        try:
            import chromadb  # noqa: F401

            from app.services.embeddings import embeddings_available

            if embeddings_available():
                return _ChromaStore(self.collection)
        except Exception as exc:  # noqa: BLE001 - fall back to keyword index
            logger.info("chroma unavailable, using keyword store: %s", exc)
        return _KeywordStore(self.collection)

    def add_chunks(self, chunks: list[Chunk]) -> None:
        self._backend.add(chunks)  # type: ignore[attr-defined]

    def query(self, text: str, k: int = 6) -> list[Retrieved]:
        return self._backend.query(text, k)  # type: ignore[attr-defined]
