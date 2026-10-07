"""Semantic search over a repo's indexed chunks (vector or keyword backend)."""
from __future__ import annotations

from app.models.repo import Repo
from app.services.vectorstore import VectorStore


def search_repo(repo: Repo, query: str, k: int = 10) -> list[dict]:
    """Return ranked results in the frontend SEARCH_RESULTS shape."""
    if not repo.chroma_collection:
        return []
    store = VectorStore(repo.chroma_collection)
    hits = store.query(query, k=k)

    results: list[dict] = []
    for h in hits:
        directory = h.path.rsplit("/", 1)[0] + "/" if "/" in h.path else ""
        snippet = "\n".join(h.content.splitlines()[:8])
        results.append(
            {
                "file": h.path,
                "path": directory,
                "line": h.start_line,
                # Normalise similarity (0-1) to a 0-100 relevance score.
                "relevance": max(1, min(100, round(h.score * 100))),
                "snippet": snippet,
            }
        )
    return results
