# CodeAtreus

Repository Onboarding Agentic Platform — paste a GitHub URL, watch it index, then
explore it through a grounded AI chat, dependency graph, flow/sequence diagrams,
a generated learning roadmap, and semantic search.

## Architecture

- **Frontend** — React 19 + Vite + Tailwind v4 (`src/App.tsx`), talking to the
  backend via the typed client in `src/api.ts`. Every page keeps its mock
  constant as the default state and overwrites it only on a successful fetch, so
  the UI still renders if the backend is offline.
- **Backend** — FastAPI service in `backend/` implementing Phases 0–3 of
  `CodeAtreus_Backend_Execution_Plan.md`. See `backend/README.md` for details.

## Run the full stack locally

**1. Backend** (zero-infra SQLite mode):

```bash
cd backend
python3.13 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="sqlite+pysqlite:///./data/dev.db"
mkdir -p data && alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

(or `docker compose up --build` in `backend/` for the full Postgres + Redis +
Celery stack.)

**2. Frontend:**

```bash
npm install
npm run dev          # http://localhost:5173
```

The frontend defaults to the backend at `http://localhost:8000/api`; override
with `VITE_API_URL`. On first entry to an app page it obtains a dev auth token
automatically (`/api/auth/dev-login`), so no GitHub OAuth setup is needed to try
the full import → index → overview → chat loop.
