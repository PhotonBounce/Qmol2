#!/bin/bash
set -euo pipefail

# ============================================================================
# ComputeSwarm — Production Deployment Script (Linux VPS)
# ============================================================================
# Usage: ./scripts/deploy.sh
#
# Prerequisites on the VPS:
#   • Docker Engine (with BuildKit)
#   • Docker Compose plugin (v2+)
#   • git (if cloning from a repo)
#   • Ports 80 and 443 open
# ============================================================================

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "=== ComputeSwarm Production Deployment ==="

# --- Prerequisites check ----------------------------------------------------
command -v docker >/dev/null 2>&1 || { echo "ERROR: Docker is not installed."; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "ERROR: Docker Compose plugin is not installed."; exit 1; }

# --- Environment setup ------------------------------------------------------
if [ ! -f .env ]; then
    if [ -f .env.prod ]; then
        echo "Copying .env.prod → .env"
        cp .env.prod .env
    else
        echo "ERROR: Neither .env nor .env.prod found."
        echo "Create one from .env.prod.example:"
        echo "  cp .env.prod.example .env.prod"
        echo "  # edit values, then run this script again"
        exit 1
    fi
fi

# Export env vars for docker-compose interpolation
set -a
source .env
set +a

# --- Build / Pull images ----------------------------------------------------
echo "Building / pulling images..."
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml build

# --- Start infrastructure ---------------------------------------------------
echo "Starting infrastructure services (db, redis, minio)..."
docker compose -f docker-compose.prod.yml up -d db redis minio

echo "Waiting for database to be ready..."
sleep 5

# --- Database migrations ----------------------------------------------------
echo "Running Alembic migrations..."
docker compose -f docker-compose.prod.yml run --rm api \
    python -m alembic upgrade head

# --- Start application ------------------------------------------------------
echo "Starting application services (api, dashboard, worker, traefik)..."
docker compose -f docker-compose.prod.yml up -d api dashboard worker traefik

# --- Health check -----------------------------------------------------------
echo ""
echo "=== Deployment Complete ==="
echo "Health:  https://${API_DOMAIN:-api.yourdomain.com}/health"
echo "Metrics: https://${API_DOMAIN:-api.yourdomain.com}/metrics"
echo "Dashboard: https://${APP_DOMAIN:-app.yourdomain.com}"
echo ""
echo "Run the following to verify:"
echo "  curl -fsS https://${API_DOMAIN:-api.yourdomain.com}/health | python -m json.tool"
