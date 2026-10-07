"""OpenRouter (OpenAI-compatible) chat client with streaming + offline fallback.

When no API key is configured the client degrades to a deterministic,
repo-aware answer built from the retrieved snippets, so chat never hard-fails in
a demo environment.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterable

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("llm")

SYSTEM_PROMPT = (
    "You are CodeAtreus, an expert code-onboarding assistant. Answer questions "
    "about the given repository using ONLY the provided code context. Cite the "
    "file paths you relied on. Prefer concise, well-structured markdown. If the "
    "context is insufficient, say so plainly."
)


def build_messages(question: str, context_blocks: Iterable[tuple[str, str]]) -> list[dict]:
    """Assemble chat messages from the question + (path, snippet) context blocks."""
    context = "\n\n".join(
        f"### {path}\n```\n{snippet}\n```" for path, snippet in context_blocks
    )
    user = f"Repository context:\n{context}\n\n---\n\nQuestion: {question}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def llm_configured() -> bool:
    return bool(settings.openrouter_api_key)


def _fallback_answer(question: str, context_blocks: list[tuple[str, str]]) -> str:
    if not context_blocks:
        return (
            "I couldn't find relevant code for that question in this repository's "
            "index. Try rephrasing or mention a specific file or symbol."
        )
    unique_paths: list[str] = []
    for path, _ in context_blocks:
        if path not in unique_paths:
            unique_paths.append(path)
    files = "\n".join(f"- `{path}`" for path in unique_paths)
    top_path, top_snippet = context_blocks[0]
    preview = "\n".join(top_snippet.splitlines()[:12])
    return (
        f"Based on the indexed code, the most relevant files for "
        f"**{question.strip()}** are:\n\n{files}\n\n"
        f"The strongest match is `{top_path}`:\n\n```\n{preview}\n```\n\n"
        f"_(LLM key not configured — this is a retrieval-grounded summary. Set "
        f"`OPENROUTER_API_KEY` for full natural-language answers.)_"
    )


async def complete(question: str, context_blocks: list[tuple[str, str]]) -> dict:
    """Non-streaming completion. Returns {answer, usage}."""
    if not llm_configured():
        return {"answer": _fallback_answer(question, context_blocks), "usage": None}

    payload = {
        "model": settings.llm_model,
        "messages": build_messages(question, context_blocks),
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://codeatreus.local",
        "X-Title": "CodeAtreus",
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as http:
            resp = await http.post(
                f"{settings.openrouter_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        return {
            "answer": data["choices"][0]["message"]["content"],
            "usage": data.get("usage"),
        }
    except Exception as exc:  # noqa: BLE001 - never let the LLM kill the request
        logger.warning("LLM call failed, using fallback: %s", exc)
        return {"answer": _fallback_answer(question, context_blocks), "usage": None}


async def stream(question: str, context_blocks: list[tuple[str, str]]) -> AsyncIterator[str]:
    """Yield answer text chunks for SSE. Falls back to a single chunk offline."""
    if not llm_configured():
        yield _fallback_answer(question, context_blocks)
        return

    payload = {
        "model": settings.llm_model,
        "messages": build_messages(question, context_blocks),
        "temperature": 0.2,
        "stream": True,
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://codeatreus.local",
        "X-Title": "CodeAtreus",
    }
    try:
        async with (
            httpx.AsyncClient(timeout=120.0) as http,
            http.stream(
                "POST",
                f"{settings.openrouter_base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as resp,
        ):
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                if data == "[DONE]":
                    break
                try:
                    delta = json.loads(data)["choices"][0]["delta"].get("content")
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
                if delta:
                    yield delta
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM stream failed, using fallback: %s", exc)
        yield _fallback_answer(question, context_blocks)
