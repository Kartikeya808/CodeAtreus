# CodeAtreus — Overnight High-Yield Implementation Plan

**Goal:** Ship a working demo by tomorrow morning. Target ~80% perceived functionality with ~20% of the effort. Make the *core loop* real; keep the rest mock-but-believable.

**Deadline reality:** ~1 night. The 8-week `CodeAtreus_Backend_Execution_Plan.md` is the north star, NOT tonight's scope. This doc overrides it for tonight.

---

## 0. Current State (verified)

- `src/App.tsx` (2226 lines) — complete, beautiful UI for all 13 pages. **Every page uses hardcoded constants** (`REPOS`, `PIPELINE_STEPS`, `CHAT_MESSAGES`, `GRAPH_NODES`, `FLOW_STEPS`, `ROADMAP_DAYS`, `SEARCH_RESULTS`…) and `setTimeout`/`setInterval` fakery. **No `fetch` calls exist.**
- `kartik/CODEATREUS/backend/app/main.py` — broken stub (`FastAPI()` used but `fastapi.FastAPI` not imported). Treat as empty.
- Stack already installed: React 19, Vite 8, Tailwind v4, Framer Motion, Recharts, lucide-react.

**Implication:** The UI is done. Tonight is 90% backend + ~10% wiring. Do NOT touch the visual design.

---

## 1. The 80/20 Cut — Tech Substitutions

Replace every heavy dependency with a zero-infra equivalent. Same demo, 1/50th the setup.

| Planned (8-week) | TONIGHT instead | Why |
|---|---|---|
| PostgreSQL + Alembic | **SQLite** (one file, `sqlmodel` or raw `sqlite3`) | No server, no migrations |
| Redis + Celery workers | **FastAPI `BackgroundTasks`** + in-memory dict for job status | Async pipeline in-process |
| ChromaDB + BGE embeddings | **Keyword/TF-IDF retrieval** over cloned files (optional: OpenAI/Jina embeddings if a key exists) | RAG-lite is enough for demo |
| Tree-sitter multi-lang AST | **File extension stats + regex** for imports/functions | Language % and "key files" look real |
| GitHub OAuth + JWT | **Fake login** (frontend already just calls `setPage('dashboard')`) — leave as-is, or trivial `/api/auth/login` returning a token | Auth is not the demo |
| LangGraph agent | **Single OpenRouter chat call** with retrieved context in the prompt | One LLM call = "agent" for demo |
| WebSockets | **SSE** or even **polling** `GET /status` every 800ms | Polling is fine for a progress bar |
| Mermaid/PlantUML services | Frontend already renders the diagram UI; **ask the LLM to emit mermaid text** | Cheap win |

**One env var:** `OPENROUTER_API_KEY` (free models: `nvidia/nemotron-...:free`, `meta-llama/llama-3.3-...:free`). If no key is available, the chat/roadmap endpoints fall back to canned-but-repo-aware responses so the demo never dies.

---

## 2. Priority Ladder (do in this order — stop whenever morning comes)

Each tier is independently demoable. Ship tier by tier.

### 🟢 TIER 1 — The Spine (MUST HAVE, ~3h)
This alone is a credible demo: *paste a real GitHub URL → watch it index → see a real overview*.

1. **`POST /api/repos/import`** — accept `{github_url}`, create SQLite row `status=queued`, kick off `BackgroundTasks`, return `{repo_id}`.
2. **Indexing pipeline (in-process)** that walks the 7 `PIPELINE_STEPS` the UI already expects and updates job status:
   - `git clone --depth 1` (GitPython or `subprocess`) into a temp dir. SSRF guard: only allow `github.com` hosts.
   - Skip `node_modules`, `.git`, `dist`, binaries, files > 1MB.
   - Walk files → count by extension → compute **language %** (maps to `LANG_DIST`).
   - Framework detection: look for `package.json`→(next/react), `pyproject.toml`/`requirements.txt`→(fastapi/django), `pom.xml`→spring, `go.mod`→go.
   - Entry points + key files: `main.*`, `index.*`, `app.*`, `README`, config files.
   - Store everything as JSON blob on the repo row.
3. **`GET /api/repos/{id}/status`** — `{step, total: 7, label, logs: [...], status}`. Drives the indexing page.
4. **`GET /api/repos/{id}/overview`** — `{language_dist, framework, entry_points, key_files, file_count, size, health}`. Health = simple heuristic (README +20, tests dir +20, lockfile +15, CI config +15, base 30).
5. **`GET /api/repos`** — list for dashboard. **`GET /api/repos/{id}`** — detail.

### 🟡 TIER 2 — The Wow (HIGH YIELD, ~2h)
Real grounded chat is the single most impressive feature.

6. **`POST /api/repos/{id}/chat`** `{message}` — retrieve top-k relevant files (keyword match on message terms against file paths + content; rank by hits), stuff snippets into a system prompt, call OpenRouter, return `{answer, files: [...paths]}`. The UI already renders markdown + file chips.
   - Streaming optional (SSE). Non-streaming is fine for v1.
7. **`GET /api/repos/{id}/search?q=`** — same retrieval, return `{file, path, line, relevance, snippet}[]` matching `SEARCH_RESULTS` shape. Pure keyword grep is acceptable.

### 🟠 TIER 3 — Fill the Pages (MEDIUM, ~2h)
Make the remaining pages pull *something* real so nothing is obviously faked.

8. **`GET /api/repos/{id}/graph`** — build nodes/edges from real import statements (regex `import ... from '...'` / `from x import`). Return `{nodes:[{id,label,type,x,y}], edges:[[a,b]]}` matching `GRAPH_NODES`/`GRAPH_EDGES`. Assign `type` by folder name heuristics (controller/service/repo/db). If time-boxed: return a simplified real graph (even 10 nodes is convincing).
9. **`POST /api/repos/{id}/roadmap`** — one LLM call: "given this file tree + key files, produce a Day 1–5 onboarding plan." Return `ROADMAP_DAYS` shape. **Fallback:** template filled with real detected dirs.
10. **`POST /api/repos/{id}/flow`** + **`/sequence`** — LLM emits ordered steps + a mermaid string. Lowest priority; mock is acceptable if out of time.

### ⚪ TIER 4 — Skip tonight (nice-to-have)
Settings/billing, security scan, dead-code, drift, timeline, API-docs, real OAuth, dashboard analytics charts (leave `DASH_ACTIVITY` mock — nobody checks). **Explicitly out of scope.**

---

## 3. Backend Skeleton (single-file friendly)

Keep it to ONE `main.py` first; split only if time allows. No Docker, no Alembic tonight.

```
backend/
├── main.py            # FastAPI app, all routes
├── indexer.py         # clone + walk + stats + retrieval helpers
├── llm.py             # OpenRouter call + fallback
├── store.py           # SQLite helpers (or just a module-level dict + sqlite for persistence)
├── requirements.txt   # fastapi uvicorn gitpython requests pydantic python-dotenv
└── data/              # cloned repos (gitignored) + codeatreus.db
```

Run: `uvicorn main:app --reload --port 8000`

**CORS:** allow `http://localhost:5173` (Vite). This is the #1 thing that silently breaks wiring — set it first.

---

## 4. Frontend Wiring (~1h, do LAST, incrementally)

The UI is done; wiring is surgical. Do it page-by-page so a failure never blocks the whole app.

1. Add `src/api.ts`: `const API = 'http://localhost:8000'` + thin `get/post` helpers. Add `VITE_API_URL` env fallback.
2. **Import page** (`ImportPage`, line ~722): on submit → `POST /import` → store `repo_id` → `setPage('indexing')`.
3. **Indexing page** (line ~824): replace the `setInterval` fake with polling `GET /status` every 800ms; drive `step`/`logs` from the response; on `status==='ready'` enable the "View Overview" button.
4. **Overview page** (line ~980): `useEffect` → `GET /overview`, map into existing JSX. Keep mock as the initial/fallback state so it renders instantly.
5. **Chat page** (line ~1129): `send()` → `POST /chat`; append real `{answer, files}`. Keep `CHAT_MESSAGES` as seed.
6. **Search page**: debounce input → `GET /search`.
7. Graph/Roadmap/Flow: wire if Tier 3 shipped; otherwise leave mock.

**Golden rule:** every page keeps its mock constant as the default state and only *overwrites on successful fetch*. That way a half-finished backend still demos perfectly.

---

## 5. Response Shapes (copy exactly — the UI already expects these)

```jsonc
// GET /api/repos/{id}/status
{ "status": "indexing", "step": 4, "total": 7,
  "label": "Embedding Generation",
  "logs": ["Cloned 847 files", "Detected Next.js", "..."] }

// GET /api/repos/{id}/overview
{ "language_dist": [{"name":"TypeScript","value":42,"color":"#3b82f6"}, ...],
  "framework": "Next.js", "file_count": 847, "size": "12.4 MB",
  "health": 97, "entry_points": ["src/main.tsx"],
  "key_files": ["package.json","vite.config.ts","README.md"] }

// POST /api/repos/{id}/chat  -> body {message}
{ "answer": "markdown string...", "files": ["src/auth/auth.service.ts"] }

// GET /api/repos/{id}/search?q=auth
[ {"file":"src/auth/auth.service.ts","path":"src/auth/","line":42,
   "relevance":98,"snippet":"..."}, ... ]

// GET /api/repos/{id}/graph
{ "nodes":[{"id":"as","label":"AuthService","type":"service","x":80,"y":400}],
  "edges":[["ac","as"]] }
```

---

## 6. Time Box (hard stops)

| Block | Target | Deliverable |
|---|---|---|
| 0:00–0:30 | Scaffold | FastAPI + CORS + SQLite + `/api/health` hit from browser |
| 0:30–3:00 | **Tier 1** | Real import → index → status → overview, wired end-to-end |
| 3:00–5:00 | **Tier 2** | Grounded chat + search working |
| 5:00–7:00 | Tier 3 | Graph (real) + roadmap (LLM), wired |
| 7:00–8:00 | Polish | Loading/error states, fallbacks, demo rehearsal |

**If behind:** Tier 1 + chat (one Tier 2 item) is already a winning demo. Protect the spine.

---

## 7. Demo Script (what you'll actually show)

1. Paste a real small repo (e.g. a FastAPI or Next.js starter — keep it <500 files for speed).
2. Watch real 7-step indexing progress.
3. Land on Overview with real language %, framework, file count, health.
4. Open Chat: "How does X work?" → grounded answer citing real files.
5. Search a term → real results. (Bonus: show the real dependency graph.)

**Pre-index 2–3 repos before the demo** so you're never waiting on a clone live.

---

## 8. Risk / Gotchas

- **CORS** — set it before anything else or wiring looks "broken."
- **Clone time** — use `--depth 1`; cap repo size; pick small demo repos.
- **No LLM key** — chat/roadmap must have a graceful canned fallback that still references real file names, so the demo survives.
- **Keep mocks as fallbacks** — never delete a constant; overwrite on fetch. A dead endpoint should degrade to the pretty mock, not a blank page.
- **Don't refactor the UI.** It's done. Resist.
