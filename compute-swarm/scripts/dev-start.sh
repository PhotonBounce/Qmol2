#!/usr/bin/env bash
set -euo pipefail

# dev-start.sh — Start infrastructure and print dev commands for ComputeSwarm
# Usage: ./scripts/dev-start.sh
# ------------------------------------------------------------------------------
# PLATFORM NOTES:
#   Linux / macOS : Run natively in Bash.
#   Windows       : Run inside Git Bash or WSL, or use .\scripts\dev-start.ps1
# ------------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ComputeSwarm — Development Mode"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ------------------------------------------------------------------
# 1. Detect Docker Compose
# ------------------------------------------------------------------
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
    echo "  Using Docker Compose (v2): docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
    echo "  Using Docker Compose (v1): docker-compose"
else
    echo "  ERROR: Docker Compose is required but not found." >&2
    exit 1
fi

# ------------------------------------------------------------------
# 2. Ensure .env exists
# ------------------------------------------------------------------
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "  →  Copying .env.example → .env"
        cp .env.example .env
    else
        echo "  ⚠  No .env or .env.example found. Continuing anyway."
    fi
fi

# ------------------------------------------------------------------
# 3. Start infrastructure
# ------------------------------------------------------------------
echo "  →  Starting infrastructure (db, redis, minio) ..."
${DOCKER_COMPOSE} up -d db redis minio

# Wait a few seconds for services to warm up
echo "  →  Waiting for services to warm up ..."
sleep 5

# ------------------------------------------------------------------
# 4. Initialize MinIO (if not already done)
# ------------------------------------------------------------------
echo "  →  Initializing MinIO ..."
"${SCRIPT_DIR}/init-minio.sh" || echo "  ⚠  MinIO init failed (may already be configured)."

# ------------------------------------------------------------------
# 5. Print dev commands
# ------------------------------------------------------------------
echo ""
echo "  ✅  Infrastructure is running."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  OPEN THESE IN SEPARATE TERMINALS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Terminal 1 — API Server:"
echo "  ─────────────────────────────────────────────"
echo "  cd backend && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "  Terminal 2 — Worker Client:"
echo "  ─────────────────────────────────────────────"
echo "  cd worker && python -m src.main --register"
echo ""
echo "  Terminal 3 — Dashboard Dev Server:"
echo "  ─────────────────────────────────────────────"
echo "  cd dashboard && npm run dev"
echo ""
echo "  Or simply open your browser to:"
echo "    • API Docs:   http://localhost:8000/docs"
echo "    • Dashboard:  http://localhost:5173  (after npm run dev)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  DOCKER SHORTCUT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  To run everything inside Docker instead:"
echo "    ${DOCKER_COMPOSE} up -d"
echo ""
