"""Learning-roadmap generator.

Uses a small LangGraph agent (plan → draft → validate) when langgraph + an LLM
key are available; otherwise produces a repo-aware templated Day 1-5 plan. Both
return the ROADMAP_DAYS shape: [{day, title, tasks[], complete}].
"""
from __future__ import annotations

import json

from app.core.config import settings
from app.core.logging import get_logger
from app.models.repo import Repo

logger = get_logger("roadmap")


def _repo_context(repo: Repo) -> dict:
    ov = repo.overview or {}
    return {
        "name": repo.name,
        "framework": ov.get("framework"),
        "language": repo.primary_language,
        "entry_points": ov.get("entry_points", []),
        "key_files": ov.get("key_files", []),
        "layers": sorted({n.get("type") for n in (repo.graph or {}).get("nodes", [])}),
    }


def _resource_links(ctx: dict, has_db: bool) -> dict[int, list[str]]:
    """Repo-aware suggested reading for each day, grounded in the detected stack."""
    fw = ctx["framework"]
    lang = ctx["language"]
    key_files = ctx["key_files"]
    manifest = next(
        (f for f in key_files if f in {
            "package.json", "pyproject.toml", "requirements.txt", "go.mod",
            "pom.xml", "Cargo.toml", "Gemfile", "build.gradle",
        }),
        None,
    )
    readme = next((f for f in key_files if f.lower().startswith("readme")), "README")
    stack = fw or lang or "the project"
    day1 = [f"{stack} documentation", f"Project {readme}"]
    if manifest:
        day1.append(f"{manifest} (dependencies & scripts)")
    else:
        day1.append("CONTRIBUTING / developer docs")
    return {
        0: day1,
        1: [
            f"{stack} routing / entry-point guide",
            "Application configuration & env setup",
            f"{lang or 'Language'} fundamentals refresher",
        ],
        2: [
            f"{stack} architecture / design-pattern guide",
            "Domain-driven design primer",
            "Clean code & refactoring references",
        ],
        3: (
            ["Data modeling & ORM documentation", "Database schema design guide",
             "Migrations & persistence best practices"]
            if has_db
            else ["External API integration guide", "HTTP client & retry patterns",
                  "API contract & error-handling references"]
        ),
        4: [
            "Testing framework documentation",
            "CI/CD pipeline reference",
            "Build, packaging & deployment guide",
        ],
    }


def _template_days(repo: Repo) -> list[dict]:
    ctx = _repo_context(repo)
    fw = ctx["framework"] or "the project"
    entries = ctx["entry_points"] or ["the main entry point"]
    has_db = "db" in ctx["layers"] or "repo" in ctx["layers"]
    reading = _resource_links(ctx, has_db)
    days: list[dict] = [
        {
            "day": 1,
            "title": "Project Structure",
            "tasks": [
                "Explore the directory layout",
                f"Read {', '.join(ctx['key_files'][:3]) or 'the manifest/config files'}",
                f"Understand the {fw} configuration",
                "Set up the local environment",
            ],
            "resources": reading[0],
            "complete": 0,
        },
        {
            "day": 2,
            "title": "Entry Points & Request Flow",
            "tasks": [
                f"Trace execution from {entries[0]}",
                "Map the routing / API surface",
                "Review middleware and configuration loading",
                "Run the app locally",
            ],
            "resources": reading[1],
            "complete": 0,
        },
        {
            "day": 3,
            "title": "Core Business Logic",
            "tasks": [
                "Study the service / domain layer",
                "Follow one feature end-to-end",
                "Identify shared utilities and abstractions",
                "Note key design patterns in use",
            ],
            "resources": reading[2],
            "complete": 0,
        },
        {
            "day": 4,
            "title": "Data Layer" if has_db else "Integrations",
            "tasks": [
                "Review data models / entities" if has_db else "Review external integrations",
                "Understand persistence or API clients",
                "Trace a read and a write path",
                "Check validation and error handling",
            ],
            "resources": reading[3],
            "complete": 0,
        },
        {
            "day": 5,
            "title": "Testing, Build & Deploy",
            "tasks": [
                "Run the test suite",
                "Review the CI/CD configuration",
                "Understand build + environment configs",
                "Read contribution / deployment docs",
            ],
            "resources": reading[4],
            "complete": 0,
        },
    ]
    return days


async def generate_roadmap(repo: Repo) -> list[dict]:
    """Produce a Day 1-5 onboarding roadmap for the repo."""
    if settings.openrouter_api_key:
        try:
            agent_days = await _run_agent(repo)
            if agent_days:
                return _backfill_resources(repo, agent_days)
        except Exception as exc:  # noqa: BLE001 - always fall back to template
            logger.warning("roadmap agent failed, using template: %s", exc)
    return _template_days(repo)


def _backfill_resources(repo: Repo, days: list[dict]) -> list[dict]:
    """Ensure every day carries suggested reading, using the template as the source."""
    template = _template_days(repo)
    for i, d in enumerate(days):
        if not d.get("resources") and i < len(template):
            d["resources"] = template[i]["resources"]
    return days


async def _run_agent(repo: Repo) -> list[dict] | None:
    """LangGraph plan→draft pipeline. Returns None if langgraph is unavailable."""
    try:
        from langgraph.graph import END, START, StateGraph
    except Exception:  # noqa: BLE001
        return await _llm_roadmap(repo)  # still try a direct LLM call

    from typing import TypedDict

    class State(TypedDict, total=False):
        context: dict
        days: list[dict]

    async def draft(state: State) -> State:
        days = await _llm_roadmap(repo)
        return {"days": days or _template_days(repo)}

    def validate(state: State) -> State:
        days = state.get("days") or []
        # Guarantee exactly 5 well-formed days.
        if len(days) != 5:
            days = _template_days(repo)
        template = _template_days(repo)
        for i, d in enumerate(days, start=1):
            d.setdefault("day", i)
            d.setdefault("complete", 0)
            d.setdefault("tasks", [])
            # Backfill reading resources from the repo-aware template if the LLM omitted them.
            if not d.get("resources"):
                d["resources"] = template[i - 1]["resources"]
        return {"days": days}

    graph = StateGraph(State)
    graph.add_node("draft", draft)
    graph.add_node("validate", validate)
    graph.add_edge(START, "draft")
    graph.add_edge("draft", "validate")
    graph.add_edge("validate", END)
    app = graph.compile()
    result = await app.ainvoke({"context": _repo_context(repo)})
    return result.get("days")


async def _llm_roadmap(repo: Repo) -> list[dict] | None:
    from app.services import llm

    ctx = json.dumps(_repo_context(repo))
    prompt = (
        "Produce a 5-day onboarding roadmap for a developer new to this repo. "
        "Return ONLY a JSON array of exactly 5 objects with keys: day (int), "
        "title (str), tasks (array of 4 short strings), resources (array of 3 "
        "short suggested-reading titles, e.g. official docs for the repo's stack), "
        "complete (int, 0). "
        "Ground the tasks and resources in the repo's actual framework, language, "
        "entry points and layers."
    )
    result = await llm.complete(prompt, [("repo.json", ctx)])
    text = result["answer"].strip()
    # Tolerate markdown code fences around the JSON.
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("[") : text.rfind("]") + 1]
    try:
        days = json.loads(text)
        if isinstance(days, list) and days:
            return days
    except json.JSONDecodeError:
        logger.info("roadmap LLM returned non-JSON; falling back to template")
    return None
