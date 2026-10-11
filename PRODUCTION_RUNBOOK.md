# CodeAtreus — Production Runbook (Render + Vercel)

Single-service v1 topology. Backend (API + in-process indexing + local Chroma)
on **Render** with a persistent disk; frontend SPA on **Vercel**; Postgres on
**Neon** (already provisioned). Config lives in `render.yaml` and `vercel.json`.

Do the steps in order — the GitHub OAuth app and the two deploys reference each
other's URLs.

---

## 0. Names / URLs (provider defaults)
These are assumed throughout. If a name is taken, pick another and update the
matching values in `render.yaml` (`CORS_ORIGINS`, `GITHUB_OAUTH_REDIRECT_URI`)
and the Vercel `VITE_API_URL`.

| Thing            | Value                                      |
|------------------|--------------------------------------------|
| Render service   | `codeatreus-api`                           |
| API base URL     | `https://codeatreus-api.onrender.com`      |
| Vercel project   | `codeatreus`                               |
| Frontend URL     | `https://codeatreus.vercel.app`            |

---

## 1. GitHub OAuth app  (yours to create)
github.com → Settings → Developer settings → **OAuth Apps → New**.
- **Homepage URL:** `https://codeatreus.vercel.app`
- **Authorization callback URL:** `https://codeatreus.vercel.app/login/callback`
  (must match `GITHUB_OAUTH_REDIRECT_URI` in `render.yaml` exactly)

Copy the **Client ID** and generate a **Client secret** — you'll paste both into
Render in the next step.

---

## 2. Backend on Render  (yours to click; config is in render.yaml)
1. Render dashboard → **New → Blueprint** → connect this GitHub repo. Render
   reads `render.yaml`.
2. When prompted, fill the four `sync: false` secrets:
   - `DATABASE_URL` → your Neon connection string (the `...-pooler...` URL from
     `backend/.env`). *Tip: if you hit prepared-statement errors, swap to Neon's
     **direct** (non-pooler) endpoint — we do our own client-side pooling.*
   - `OPENROUTER_API_KEY` → from `backend/.env`
   - `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` → from step 1
3. Apply. Render builds the Docker image, runs `alembic upgrade head`
   (preDeploy), mounts the 10 GB disk at `/app/data`, and starts uvicorn.
   `JWT_SECRET` is auto-generated and stays stable across deploys.
4. Verify: `curl https://codeatreus-api.onrender.com/api/health` → healthy.
   `curl -X POST https://codeatreus-api.onrender.com/api/auth/dev-login` → 404
   (dev-login is disabled in production — this is correct).

> Note: the Starter plan (~$7/mo) is required — the persistent disk isn't
> available on the free tier, and free services spin down on idle.

---

## 3. Frontend on Vercel  (yours to click; config is in vercel.json)
1. Vercel → **Add New → Project** → import this repo. Root directory = repo root
   (Vite is auto-detected; `vercel.json` sets build/output/SPA-rewrite).
2. Project **Settings → Environment Variables**, add:
   - `VITE_API_URL` = `https://codeatreus-api.onrender.com/api`
     (baked in at build time — set it **before** the first build)
3. Deploy. Confirm the app loads at `https://codeatreus.vercel.app`.

---

## 4. End-to-end check
Open `https://codeatreus.vercel.app`, log in with **GitHub** (dev-login is off),
paste a small public repo, and watch the 7-step indexing run. Overview / chat /
graph / search should populate from real data.

Troubleshooting:
- **Login loops / OAuth error** → callback URL mismatch (step 1 vs
  `GITHUB_OAUTH_REDIRECT_URI`), or `CORS_ORIGINS` ≠ the real Vercel URL.
- **Chat says "LLM key not configured"** → `OPENROUTER_API_KEY` not set on Render.
- **Indexing finishes but overview is empty** → disk not mounted; confirm the
  Render disk at `/app/data` and that `CLONE_DIR`/`CHROMA_PERSIST_DIR` point under it.

---

## Later: scaling out
To run replicated Celery workers (separate from the API) you must move cloned
repos off local disk to shared/object storage and switch Chroma to server mode
(`CHROMA_MODE=http` — already supported in code). Until then, keep the single
service; it indexes one repo at a time per process.
