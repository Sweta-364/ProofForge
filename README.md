# ProofForge

ProofForge is an AI-powered developer simulation platform where students fix real-world broken codebases in a browser IDE, receive senior-engineer-level AI code review, and earn a cryptographically signed DevPortfolio Card that proves what they can actually build. It targets the gap between course certificates and demonstrated coding ability — only 4.4% of Indian CS graduates can write working code on day one.

---

## Run It Locally (any PC) — Quick Start

### Step 1 — Install these two things manually (once)

| Tool | Why | Get it |
|------|-----|--------|
| **Docker Desktop** | Runs the database, cache, storage, API, and code sandboxes | https://www.docker.com/products/docker-desktop — install, start it, wait until it says "Engine running" |
| **Node.js 18+** | Runs the React frontend dev server | https://nodejs.org (LTS version) |

That's it. You do **not** need Python, PostgreSQL, Redis, or any API keys — everything else is installed automatically inside Docker on first run.

### Step 2 — Clone and run one command

**Windows (PowerShell):**
```powershell
git clone <repo-url>
cd <repo-folder>
.\dev.ps1
```

**macOS / Linux:**
```bash
git clone <repo-url>
cd <repo-folder>
chmod +x dev.sh
./dev.sh
```

The first run takes a few minutes — it automatically:
1. Creates a `.env` file with freshly generated secrets (JWT secret + Ed25519 signing keys)
2. Builds all Docker images (API + sandbox runner) and starts postgres/redis/minio/api
3. Seeds the 5 problems and a demo portfolio into the database
4. Installs frontend dependencies (`npm install`)
5. Opens http://localhost:5173 in your browser and starts the Vite dev server

Every later run does the same but skips what's already done, so it starts in seconds. Use `.\dev.ps1 -SkipSeed` (or `./dev.sh --skip-seed`) to skip re-seeding.

### Step 3 — Sign in and explore

On the login page click the **"Testing - skip sign in (dev only)"** button — no GitHub account or keys needed. You land on the dashboard; from there pick a track, open the workspace, fix the code, run tests, and submit. AI reviews run in **mock mode** by default (deterministic, no API key), so the entire flow works offline.

### Stopping

`Ctrl+C` stops the frontend. The Docker stack keeps running in the background; stop it with:
```bash
docker compose down
```

---

## Optional: Real Sign-In and Real AI Reviews

Local dev works fully without these. Add them to `.env` only if you want the production behavior (restart the api after changes: `docker compose up -d api`).

**Real GitHub sign-in** — create an OAuth app at https://github.com/settings/applications/new with:
- Homepage URL: `http://localhost:5173`
- Authorization callback URL: `http://localhost:8000/api/v1/auth/callback`

then set `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` in `.env`.

**Real AI reviews** — pick one in `.env`:

| `REVIEW_PROVIDER` | Needs | Notes |
|--------------------|-------|-------|
| `mock` (default for dev) | nothing | Deterministic review built from test/AST/security results |
| `openai_compat` | free key from https://console.groq.com in `DEV_LLM_API_KEY` | Real LLM review, free tier |
| `anthropic` | `ANTHROPIC_API_KEY` | Production setting — Claude Sonnet |

Before deploying anywhere: set `DEV_MODE=false` (removes the dev-login bypass) and `REVIEW_PROVIDER=anthropic`.

---

## Project Tour

```
backend/            FastAPI + asyncpg (raw SQL) + aioredis
  app/auth/         GitHub OAuth2 + JWT (+ dev-login bypass when DEV_MODE=true)
  app/problems/     problem delivery + sessions
  app/submissions/  pipeline: sandbox tests -> AST + Bandit -> AI review
  app/portfolio/    Ed25519-signed portfolio cards
  app/websocket/    live submission status streaming
  migrations/       001_initial.sql (auto-runs on first postgres start), 002 seed script
  sandbox/          Docker sandbox runner
  tests/            pytest suite (41 tests)
frontend/           React 19 + Vite + TypeScript + Tailwind + Monaco editor
problems/           the 5 broken codebases + their test suites + meta.json
docker/runners/     sandbox Docker image (network-isolated python runner)
scripts/            seed_demo.py, generate_keys.py
dev.ps1 / dev.sh    one-command local startup (this is what you run)
```

### URLs once running

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API + docs | http://localhost:8000/docs |
| MinIO console | http://localhost:9001 (minioadmin / miniopassword) |
| Demo portfolio | http://localhost:5173/p/proofforge_demo |

### The 5 problems

| # | Slug | Level | What to fix |
|---|------|-------|-------------|
| 1 | `001-cors-fix` | Junior | Add `CORSMiddleware` to a bare FastAPI app |
| 2 | `002-input-validation` | Junior+ | Fix 500 crash on special characters in login |
| 3 | `003-memory-leak` | Mid | Replace unbounded dict cache with TTL cache |
| 4 | `004-slow-query` | Mid+ | Add missing index, fix N+1 query |
| 5 | `005-race-condition` | Senior | Add `asyncio.Lock` to shared async state |

---

## Running Tests

Backend tests need host Python 3.12 with `pip install -r backend/requirements.txt`, the stack running, and **must be run from the repo root**:

```powershell
# Windows — point host-run tests at the dockerized services:
$env:DATABASE_URL   = "postgresql://proofforge:password@localhost:5432/proofforge"
$env:MINIO_ENDPOINT = "localhost:9000"
$env:REDIS_URL      = "redis://localhost:6379"
$env:SANDBOX_TEMP_DIR = "$PWD\.sandbox-tmp"
python -m pytest backend/tests/ -q
```

Frontend (no env setup needed):
```bash
cd frontend
npm run typecheck    # 0 errors expected
npm run test         # vitest suite
```

Note: the backend suite truncates DB tables — re-run `.\dev.ps1` (or just the seed step) afterwards to restore the problems and demo data.

---

## Troubleshooting

- **`docker compose up` can't pull `minio/minio`** (Docker Hub CDN hiccup): pull from the mirror and retag:
  `docker pull quay.io/minio/minio:latest && docker tag quay.io/minio/minio:latest minio/minio:latest`
- **API unhealthy / port already in use**: something else is on 8000/5173/5432/6379/9000 — stop it or change the port mapping in `docker-compose.yml`.
- **Submissions fail with a Docker error**: make sure Docker Desktop is running and the sandbox image exists (`docker images proofforge/python-runner` — `dev.ps1` builds it automatically).
- **Stale stack after pulling new code**: `docker compose down && .\dev.ps1` rebuilds everything.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI, asyncpg (raw SQL, no ORM), Uvicorn |
| AI Review | Anthropic Claude (prod) / OpenAI-compatible (Groq) / mock |
| Analysis | tree-sitter AST + Bandit security scan |
| Sandbox | Docker SDK — network-isolated, 256 MB, read-only containers |
| Crypto | PyNaCl Ed25519 portfolio signing |
| Data | PostgreSQL 16, Redis 7, MinIO (S3-compatible) |
| Frontend | React 19, Vite 6, TypeScript, Tailwind v4, Monaco editor |
| Auth | GitHub OAuth2 + python-jose JWT |

## Production Build

```bash
docker compose -f docker-compose.prod.yml up --build
```
4 Uvicorn workers, no reload, internal-only db/cache ports, nginx serves the built React bundle and proxies `/api`.
