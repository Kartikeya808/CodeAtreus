"""Split source files into overlapping line-window chunks for embedding."""
from __future__ import annotations

from app.services.indexing.walk import SourceFile
from app.services.vectorstore import Chunk

CHUNK_LINES = 60
OVERLAP_LINES = 10
MAX_CHUNKS_PER_FILE = 40


def chunk_files(files: list[SourceFile]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for sf in files:
        if sf.language is None:
            continue
        try:
            text = sf.abs_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lines = text.splitlines()
        if not lines:
            continue
        step = max(CHUNK_LINES - OVERLAP_LINES, 1)
        produced = 0
        for start in range(0, len(lines), step):
            window = lines[start : start + CHUNK_LINES]
            body = "\n".join(window).strip()
            if not body:
                continue
            chunks.append(
                Chunk(
                    id=f"{sf.rel_path}:{start + 1}",
                    path=sf.rel_path,
                    content=body,
                    start_line=start + 1,
                )
            )
            produced += 1
            if produced >= MAX_CHUNKS_PER_FILE:
                break
    return chunks
