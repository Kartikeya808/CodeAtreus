"""Embedding provider wiring for ChromaDB.

Default provider is local fastembed (BGE-small). The functions here only report
availability and build a Chroma-compatible embedding function; when the stack is
absent callers fall back to the keyword store in vectorstore.py.
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("embeddings")


@lru_cache
def embeddings_available() -> bool:
    provider = settings.embedding_provider.lower()
    if provider == "fastembed":
        try:
            import fastembed  # noqa: F401
            return True
        except Exception:  # noqa: BLE001
            return False
    if provider in ("jina", "openai-compatible"):
        return bool(settings.jina_api_key or settings.openrouter_api_key)
    return False


def get_embedding_function():
    """Return a Chroma `EmbeddingFunction` for the configured provider."""
    provider = settings.embedding_provider.lower()
    if provider == "fastembed":
        from chromadb.utils.embedding_functions import (
            DefaultEmbeddingFunction,
        )

        try:
            from chromadb.utils.embedding_functions import (
                FastEmbedEmbeddingFunction,
            )

            return FastEmbedEmbeddingFunction(model_name=settings.embedding_model)
        except Exception as exc:  # noqa: BLE001
            logger.info("FastEmbed EF unavailable (%s); using Chroma default", exc)
            return DefaultEmbeddingFunction()

    if provider in ("jina", "openai-compatible"):
        from chromadb.utils.embedding_functions import (
            OpenAIEmbeddingFunction,
        )

        api_base = (
            "https://api.jina.ai/v1" if provider == "jina" else settings.openrouter_base_url
        )
        return OpenAIEmbeddingFunction(
            api_key=settings.jina_api_key or settings.openrouter_api_key,
            api_base=api_base,
            model_name=settings.embedding_model,
        )

    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

    return DefaultEmbeddingFunction()
