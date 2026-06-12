#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# ProofForge - one-command dev environment (macOS / Linux)
#
#   ./dev.sh             start everything (first run also installs everything)
#   ./dev.sh --skip-seed start without re-running the seed scripts
#
# Same behavior as dev.ps1 - see that file or README.md for details.
# Prerequisites (install manually, once): Docker (running), Node.js 18+
# -----------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")"

SKIP_SEED=false
[ "${1:-}" = "--skip-seed" ] && SKIP_SEED=true

# -- [1/6] Prerequisite checks ------------------------------------------------
echo "[1/6] Checking prerequisites..."
docker info >/dev/null 2>&1 || { echo "ERROR: Docker is not available. Install Docker, start it, and re-run."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "ERROR: Node.js is not installed. Install Node.js 18+ and re-run."; exit 1; }

# -- [2/6] Bootstrap .env on first run ----------------------------------------
if [ ! -f .env ]; then
    echo "[2/6] No .env found - creating one with generated secrets..."
    cp .env.example .env
    JWT=$(LC_ALL=C tr -dc 'a-f0-9' </dev/urandom | head -c 64)
    sed -i.bak \
        -e "s/^JWT_SECRET=.*/JWT_SECRET=${JWT}/" \
        -e "s/^DEV_MODE=.*/DEV_MODE=true/" \
        -e "s/^REVIEW_PROVIDER=.*/REVIEW_PROVIDER=mock/" \
        .env && rm -f .env.bak

    echo "      Building api image to generate signing keys..."
    docker compose build api
    KEYS=$(docker compose run --rm --no-deps --entrypoint python api /app/scripts/generate_keys.py)
    PRIV=$(echo "$KEYS" | grep '^PORTFOLIO_SIGNING_PRIVATE_KEY=')
    PUB=$(echo "$KEYS" | grep '^PORTFOLIO_SIGNING_PUBLIC_KEY=')
    [ -n "$PRIV" ] && [ -n "$PUB" ] || { echo "ERROR: could not parse generated signing keys"; exit 1; }
    sed -i.bak \
        -e "s|^PORTFOLIO_SIGNING_PRIVATE_KEY=.*|${PRIV}|" \
        -e "s|^PORTFOLIO_SIGNING_PUBLIC_KEY=.*|${PUB}|" \
        .env && rm -f .env.bak
    echo "      .env created (DEV_MODE=true, mock AI reviews - no API keys needed)."
else
    echo "[2/6] .env exists - keeping it."
fi

# -- [3/6] Sandbox runner image -----------------------------------------------
if [ -z "$(docker images -q proofforge/python-runner:3.12)" ]; then
    echo "[3/6] Building sandbox runner image (one-time)..."
    docker build -t proofforge/python-runner:3.12 docker/runners/python/
else
    echo "[3/6] Sandbox runner image present."
fi

# -- [4/6] Docker stack ---------------------------------------------------------
echo "[4/6] Starting docker stack (postgres, redis, minio, api)..."
docker compose up -d --build

echo "      Waiting for API health..."
HEALTHY=false
for _ in $(seq 1 30); do
    sleep 2
    if curl -sf http://localhost:8000/api/v1/health | grep -q '"ok"'; then HEALTHY=true; break; fi
done
if [ "$HEALTHY" != true ]; then
    docker compose logs api --tail 30
    echo "ERROR: API did not become healthy within 60s - see logs above"
    exit 1
fi
echo "      API healthy."

# -- [5/6] Seed problems + demo account (runs inside the api container) --------
if [ "$SKIP_SEED" = false ]; then
    echo "[5/6] Seeding problems + demo account (idempotent)..."
    docker compose exec -T api python migrations/002_seed_problems.py
    docker compose exec -T api python /app/scripts/seed_demo.py
else
    echo "[5/6] Skipping seeds (--skip-seed)."
fi

# -- [6/6] Frontend -------------------------------------------------------------
echo "[6/6] Starting frontend dev server..."
cd frontend
[ -d node_modules ] || { echo "      Installing frontend dependencies (one-time)..."; npm install; }
( command -v open >/dev/null 2>&1 && open http://localhost:5173 ) || \
( command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:5173 ) || true
npm run dev
