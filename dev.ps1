# -----------------------------------------------------------------------------
# ProofForge - one-command dev environment (Windows)
#
#   .\dev.ps1            start everything (first run also installs everything)
#   .\dev.ps1 -SkipSeed  start without re-running the seed scripts
#
# First run: creates .env with generated secrets, builds all Docker images,
# seeds the database, installs frontend deps. Every run: starts the docker
# stack (postgres/redis/minio/api), seeds (idempotent), runs the Vite dev
# server and opens the browser. Ctrl+C stops the frontend; the docker stack
# keeps running (stop it with: docker compose down).
#
# Prerequisites (install manually, once): Docker Desktop (running), Node.js 18+
#
# NOTE: keep this file ASCII-only. Windows PowerShell 5.1 reads BOM-less
# .ps1 files as ANSI, so smart quotes / em-dashes break the parser.
# -----------------------------------------------------------------------------
param([switch]$SkipSeed)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# -- [1/6] Prerequisite checks ------------------------------------------------
Write-Host "[1/6] Checking prerequisites..." -ForegroundColor Cyan
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker is not available. Install Docker Desktop, start it, and wait for 'Engine running'."
}
try { node --version *> $null } catch {
    throw "Node.js is not installed. Install Node.js 18+ from https://nodejs.org and re-run."
}
Write-Host "      Docker + Node found." -ForegroundColor Green

# -- [2/6] Bootstrap .env on first run ----------------------------------------
if (-not (Test-Path .env)) {
    Write-Host "[2/6] No .env found - creating one with generated secrets..." -ForegroundColor Cyan
    Copy-Item .env.example .env
    $envText = Get-Content .env -Raw

    # Random 256-bit JWT secret
    $jwt = -join ((1..64) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })
    $envText = $envText -replace '(?m)^JWT_SECRET=.*', "JWT_SECRET=$jwt"

    # Dev-friendly defaults: Testing login button + LLM-free mock reviews,
    # so no GitHub OAuth or Anthropic keys are needed to run locally.
    $envText = $envText -replace '(?m)^DEV_MODE=.*', 'DEV_MODE=true'
    $envText = $envText -replace '(?m)^REVIEW_PROVIDER=.*', 'REVIEW_PROVIDER=mock'
    Set-Content .env $envText -Encoding ascii

    # Ed25519 portfolio signing keys - generated inside the api image (has PyNaCl)
    Write-Host "      Building api image to generate signing keys..." -ForegroundColor Cyan
    docker compose build api
    if ($LASTEXITCODE -ne 0) { throw "docker compose build api failed" }
    $keyOutput = docker compose run --rm --no-deps --entrypoint python api /app/scripts/generate_keys.py
    if ($LASTEXITCODE -ne 0) { throw "signing key generation failed" }
    $priv = ($keyOutput | Select-String '^PORTFOLIO_SIGNING_PRIVATE_KEY=').Line
    $pub  = ($keyOutput | Select-String '^PORTFOLIO_SIGNING_PUBLIC_KEY=').Line
    if (-not $priv -or -not $pub) { throw "could not parse generated signing keys" }
    $envText = Get-Content .env -Raw
    $envText = $envText -replace '(?m)^PORTFOLIO_SIGNING_PRIVATE_KEY=.*', $priv
    $envText = $envText -replace '(?m)^PORTFOLIO_SIGNING_PUBLIC_KEY=.*', $pub
    Set-Content .env $envText -Encoding ascii
    Write-Host "      .env created (DEV_MODE=true, mock AI reviews - no API keys needed)." -ForegroundColor Green
} else {
    Write-Host "[2/6] .env exists - keeping it." -ForegroundColor Yellow
}

# -- [3/6] Sandbox runner image (used to run student code in isolation) -------
$runnerImage = docker images -q proofforge/python-runner:3.12
if (-not $runnerImage) {
    Write-Host "[3/6] Building sandbox runner image (one-time)..." -ForegroundColor Cyan
    docker build -t proofforge/python-runner:3.12 docker/runners/python/
    if ($LASTEXITCODE -ne 0) { throw "runner image build failed" }
} else {
    Write-Host "[3/6] Sandbox runner image present." -ForegroundColor Green
}

# -- [4/6] Docker stack -------------------------------------------------------
Write-Host "[4/6] Starting docker stack (postgres, redis, minio, api)..." -ForegroundColor Cyan
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }

Write-Host "      Waiting for API health..." -ForegroundColor Cyan
$healthy = $false
foreach ($i in 1..30) {
    Start-Sleep -Seconds 2
    try {
        $resp = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -TimeoutSec 3
        if ($resp.status -eq "ok") { $healthy = $true; break }
    } catch { }
}
if (-not $healthy) {
    docker compose logs api --tail 30
    throw "API did not become healthy within 60s - see logs above"
}
Write-Host "      API healthy." -ForegroundColor Green

# -- [5/6] Seed problems + demo account (runs inside the api container) -------
if (-not $SkipSeed) {
    Write-Host "[5/6] Seeding problems + demo account (idempotent)..." -ForegroundColor Cyan
    docker compose exec -T api python migrations/002_seed_problems.py
    if ($LASTEXITCODE -ne 0) { throw "problem seeding failed" }
    docker compose exec -T api python /app/scripts/seed_demo.py
    if ($LASTEXITCODE -ne 0) { throw "demo seeding failed" }
} else {
    Write-Host "[5/6] Skipping seeds (-SkipSeed)." -ForegroundColor Yellow
}

# -- [6/6] Frontend -----------------------------------------------------------
Write-Host "[6/6] Starting frontend dev server..." -ForegroundColor Cyan
Set-Location frontend
if (-not (Test-Path node_modules)) {
    Write-Host "      Installing frontend dependencies (one-time)..." -ForegroundColor Cyan
    npm install
    if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
}
Start-Process "http://localhost:5173"
npm run dev
