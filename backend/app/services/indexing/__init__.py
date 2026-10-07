"""Async indexing pipeline — clone, parse, extract, embed, graph.

The heavy analysis dependencies (tree-sitter, chromadb, fastembed) are optional
at runtime: each stage falls back to a lightweight implementation when its
library is unavailable, so the pipeline runs end-to-end everywhere while using
the full stack in the Docker image.
"""
from app.services.indexing.dispatch import enqueue_indexing
from app.services.indexing.pipeline import run_index_pipeline

__all__ = ["enqueue_indexing", "run_index_pipeline"]
