# CodeAtreus Backend

FastAPI backend powering the CodeAtreus repository-onboarding platform.
Implements **Phase 0 (foundations)**, **Phase 1 (import → index → overview →
chat)**, **Phase 2 (architecture, roadmap, graph, dashboard)** and **Phase 3
(flow, sequence diagrams, search, api-docs)** of
`../CodeAtreus_Backend_Execution_Plan.md`.

## Stack

| Concern | Tech |
|---|---|
| API | FastAPI + Uvicorn |
| Auth | GitHub OAuth + JWT (access/refresh) |
| DB | PostgreSQL (SQLAlchemy 2.0 + Alembic) |
| Queue | Celery + Redis (async indexing) |
| Static analysis | tree-sitter (regex fallback), NetworkX |
| Embeddings / RAG | ChromaDB + fastembed (keyword fallback) |
| LLM | OpenRouter (OpenAI-compatible), repo-aware offline fallback |

Every heavy analysis dependency degrades gracefully when absent, so the whole
pipeline runs with only the core deps installed (and in CI).

## Run with Docker (full stack)

```bash
cp .env.example .env          # fill in GITHUB_* and OPENROUTER_API_KEY if you have them
docker compose up --build     # api :8000, postgres :5432, redis :6379, celery worker
```

The `api` service runs `alembic upgrade head` on start. Health check:
`curl http://localhost:8000/api/health`.

## Run locally (no infra, SQLite + in-process indexing)

```bash
python3.13 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="sqlite+pysqlite:///./data/dev.db"
mkdir -p data && alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Without Redis, `enqueue_indexing` runs the pipeline in a background thread, so
import → index → overview → chat all work single-process.

## Key endpoints

| Method | Path | Page |
|---|---|---|
| POST | `/api/auth/github` · `/api/auth/refresh` · `/api/auth/dev-login` | login |
| GET | `/api/auth/me` | — |
| POST | `/api/repos/import` | import |
| GET | `/api/repos` · `/api/repos/{id}` | dashboard / overview |
| GET | `/api/repos/{id}/status` · WS `/ws/indexing/{id}` | indexing |
| GET | `/api/repos/{id}/overview` | overview |
| POST | `/api/repos/{id}/chat` · `/chat/stream` (SSE) | chat |
| GET | `/api/repos/{id}/chat/history` | chat |
| POST | `/api/repos/{id}/architecture-summary` | overview (deep) |
| GET | `/api/repos/{id}/important-files` | overview |
| GET | `/api/repos/{id}/roadmap` · POST `/roadmap/generate` | roadmap |
| GET | `/api/repos/{id}/graph` | graph |
| POST | `/api/repos/{id}/flow` | flow |
| POST | `/api/repos/{id}/sequence` | sequence |
| GET | `/api/repos/{id}/search?q=` | search |
| GET | `/api/repos/{id}/api-docs` | api docs |
| GET | `/api/dashboard/stats` · `/api/dashboard/activity` | dashboard |

`POST /api/auth/dev-login` is disabled when `ENVIRONMENT=production`; use it to
wire the frontend before real GitHub OAuth credentials exist.

## Dev commands

```bash
ruff check app tests     # lint
mypy app                 # type-check
pytest                   # tests (SQLite, in-memory; real pipeline run included)
alembic revision --autogenerate -m "msg"
```
