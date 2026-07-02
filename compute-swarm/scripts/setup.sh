#!/usr/bin/env bash
set -euo pipefail

# setup.sh — Master local development setup for ComputeSwarm
# Usage: ./scripts/setup.sh
# ------------------------------------------------------------------------------
# PLATFORM NOTES:
#   Linux / macOS : Run natively in Bash.
#   Windows       : Run inside Git Bash (ships with Git for Windows) or WSL.
#                   PowerShell users: run .\scripts\setup.ps1 instead.
# ------------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# ------------------------------------------------------------------
# Helper: print error and exit
# ------------------------------------------------------------------
error_exit() {
    echo ""
    echo "❌  ERROR: $1" >&2
    echo ""
    exit 1
}

# ------------------------------------------------------------------
# Helper: print section header
# ------------------------------------------------------------------
section() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  $1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

section "ComputeSwarm — Local Development Setup"

# ------------------------------------------------------------------
# 1. Check prerequisites
# ------------------------------------------------------------------
section "1. Checking Prerequisites"

check_prereq() {
    local cmd="$1"
    local name="$2"
    if command -v "${cmd}" >/dev/null 2>&1; then
        echo "   ✓  ${name} found: $(command -v "${cmd}")"
    else
        error_exit "${name} (${cmd}) is required but not found."
    fi
}

check_prereq docker "Docker"

# Docker Compose detection (v1 plugin vs v2)
if docker compose version >/dev/null 2>&1; then
    echo "   ✓  Docker Compose (v2) found: docker compose"
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    echo "   ✓  Docker Compose (v1) found: $(command -v docker-compose)"
    DOCKER_COMPOSE="docker-compose"
else
    error_exit "Docker Compose is required but not found."
fi

check_prereq python3 "Python 3"

PYTHON_VERSION=$(python3 --version 2>/dev/null | awk '{print $2}')
echo "   ℹ  Python version: ${PYTHON_VERSION}"

# Python version check (require >= 3.10)
PYTHON_MAJOR=$(echo "${PYTHON_VERSION}" | cut -d. -f1)
PYTHON_MINOR=$(echo "${PYTHON_VERSION}" | cut -d. -f2)
if [ "${PYTHON_MAJOR}" -lt 3 ] || ([ "${PYTHON_MAJOR}" -eq 3 ] && [ "${PYTHON_MINOR}" -lt 10 ]); then
    error_exit "Python 3.10+ is required. Found ${PYTHON_VERSION}."
fi

# Node.js is optional — only needed for local dashboard dev
if command -v node >/dev/null 2>&1; then
    NODE_VERSION=$(node --version 2>/dev/null)
    echo "   ✓  Node.js found: ${NODE_VERSION}"
    NODE_MAJOR=$(echo "${NODE_VERSION}" | sed 's/^v//' | cut -d. -f1)
    if [ "${NODE_MAJOR}" -lt 18 ]; then
        echo "   ⚠  Node.js 18+ recommended for dashboard dev. Found ${NODE_VERSION}." >&2
    fi
else
    echo "   ⚠  Node.js not found (optional — only needed for local dashboard dev)."
fi

# ------------------------------------------------------------------
# 2. Environment file
# ------------------------------------------------------------------
section "2. Environment File"

if [ ! -f ".env" ]; then
    echo "   →  Copying .env.example → .env"
    cp .env.example .env
    echo "   ✓  .env created. Review it and adjust any secrets/URLs if needed."
else
    echo "   ✓  .env already exists. Skipping copy."
fi

# ------------------------------------------------------------------
# 3. Start core infrastructure
# ------------------------------------------------------------------
section "3. Starting Infrastructure (db, redis, minio)"

${DOCKER_COMPOSE} up -d db redis minio || error_exit "Failed to start infrastructure services."
echo "   ✓  Infrastructure containers started."

# ------------------------------------------------------------------
# 4. Build docker-jobs images
# ------------------------------------------------------------------
section "4. Building Docker Job Images"

build_image() {
    local tag="$1"
    local context="$2"
    if docker image inspect "${tag}" >/dev/null 2>&1; then
        echo "   ✓  Image ${tag} already exists. Skipping build."
    else
        echo "   →  Building ${tag} ..."
        docker build -q -t "${tag}" "${context}" || error_exit "Failed to build ${tag}."
        echo "   ✓  ${tag} built."
    fi
}

build_image "computeswarm/base:latest"          "docker-jobs/base/"
build_image "computeswarm/physics-sim:latest"   "docker-jobs/examples/physics-sim/"
build_image "computeswarm/blender-render:latest" "docker-jobs/examples/blender-render/"
build_image "computeswarm/molecular-dock:latest" "docker-jobs/examples/molecular-dock/"

# ------------------------------------------------------------------
# 5. Initialize MinIO bucket
# ------------------------------------------------------------------
section "5. Initializing MinIO Object Storage"

"${SCRIPT_DIR}/init-minio.sh" || error_exit "MinIO initialization failed."

# ------------------------------------------------------------------
# 6. Backend setup
# ------------------------------------------------------------------
section "6. Backend Setup"

if [ -d "backend" ]; then
    cd backend

    # Create virtual environment if not present
    if [ ! -d "venv" ]; then
        echo "   →  Creating Python virtual environment (venv) ..."
        python3 -m venv venv || error_exit "Failed to create Python venv."
        echo "   ✓  venv created."
    else
        echo "   ✓  venv already exists."
    fi

    # Activate venv (best-effort cross-platform)
    VENV_ACTIVATED=false
    if [ -f "venv/bin/activate" ]; then
        # shellcheck source=/dev/null
        source venv/bin/activate
        VENV_ACTIVATED=true
    elif [ -f "venv/Scripts/activate" ]; then
        # shellcheck source=/dev/null
        source venv/Scripts/activate
        VENV_ACTIVATED=true
    fi

    if [ "${VENV_ACTIVATED}" != "true" ]; then
        error_exit "Could not activate virtual environment. Expected venv/bin/activate or venv/Scripts/activate."
    fi

    echo "   →  Installing Python requirements ..."
    pip install --quiet --upgrade pip || true
    pip install -r requirements.txt || error_exit "Failed to install backend Python requirements."
    echo "   ✓  Backend requirements installed."

    # Run migrations
    if [ -f "alembic.ini" ]; then
        echo "   →  Running Alembic migrations ..."
        alembic upgrade head || error_exit "Alembic migration failed."
        echo "   ✓  Database migrated to latest revision."
    else
        echo "   ⚠  No alembic.ini found; skipping migrations."
    fi

    # Optional: seed admin user
    if [ -f "scripts/seed_admin.py" ]; then
        echo "   →  Seeding admin user ..."
        python scripts/seed_admin.py || echo "   ⚠  Admin seed script returned non-zero (continuing)."
    fi

    cd "${PROJECT_ROOT}"
else
    echo "   ⚠  No backend/ directory found; skipping backend setup."
fi

# ------------------------------------------------------------------
# 7. Dashboard setup
# ------------------------------------------------------------------
section "7. Dashboard Setup"

if [ -d "dashboard" ]; then
    cd dashboard
    if [ -f "package.json" ]; then
        if [ -d "node_modules" ]; then
            echo "   ✓  node_modules already exists. Skipping npm install."
        else
            echo "   →  Running npm install ..."
            npm install || error_exit "npm install failed."
            echo "   ✓  Dashboard dependencies installed."
        fi
    else
        echo "   ⚠  No package.json in dashboard; skipping npm install."
    fi
    cd "${PROJECT_ROOT}"
else
    echo "   ⚠  No dashboard/ directory found; skipping dashboard setup."
fi

# ------------------------------------------------------------------
# 8. Done
# ------------------------------------------------------------------
section "Setup Complete!"

cat <<'EOF'

🎉  ComputeSwarm is ready for local development.

───────────────────────────────────────────────────────────────
  NEXT STEPS — Run each command in a separate terminal
───────────────────────────────────────────────────────────────

  1. Infrastructure (already started by this script):
     docker compose up -d db redis minio

  2. Start the API server:
     cd backend && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

  3. Start the worker client:
     cd worker && python -m src.main --register

  4. Start the dashboard dev server:
     cd dashboard && npm run dev

     (Or visit http://localhost:8000/docs for the Swagger API UI.)

───────────────────────────────────────────────────────────────
  SHORTCUTS
───────────────────────────────────────────────────────────────

  • Run all services via Docker (production-like):
    docker compose up -d

  • Run tests:
    make test-smoke
    make test-e2e
    make test-integration

  • Stop infrastructure:
    docker compose down

  For Windows PowerShell users, use .\scripts\setup.ps1 instead.

EOF
