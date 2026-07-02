# Contributing to ComputeSwarm

Thank you for your interest in contributing! This guide covers how to set up your development environment, run tests, and extend the platform with new job types.

## Development Environment Setup

### Prerequisites

- **Docker Desktop** (4.25+) with Docker Compose v2
- **Python** 3.10+
- **Node.js** 18+ (for dashboard work)
- **Git** 2.40+

### Quick Setup

```bash
# Linux / macOS / Git Bash
./scripts/setup.sh

# Windows PowerShell
.\scripts\setup.ps1
```

This will:
1. Verify prerequisites
2. Copy `.env.example` → `.env`
3. Start PostgreSQL, Redis, and MinIO containers
4. Build Docker job images (`computeswarm/base`, `computeswarm/physics-sim`, etc.)
5. Initialize the MinIO bucket
6. Create a Python virtual environment, install dependencies, and run Alembic migrations
7. Install Node.js dependencies for the dashboard
8. Optionally seed demo data (`backend/scripts/seed.py`)

### Start Developing

Open **four separate terminals** and run:

| Terminal | Command | Purpose |
|----------|---------|---------|
| 1 | `docker compose up -d db redis minio` | Infrastructure |
| 2 | `cd backend && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` | API Server |
| 3 | `cd worker && python -m src.main --register` | Worker Client |
| 4 | `cd dashboard && npm run dev` | Dashboard Dev Server |

Or use the convenience script:

```bash
./scripts/dev-start.sh       # Git Bash / Linux / macOS
.\scripts\dev-start.ps1      # Windows PowerShell
```

## Running Tests

We provide three test suites, each exercising a different scope:

```bash
# Fast smoke test (API health + basic job flow)
make test-smoke
# or: python scripts/test-smoke.py

# End-to-end test (submit → run → validate → download)
make test-e2e
# or: python scripts/test-e2e.py

# Integration test (infrastructure + API + DB + storage)
make test-integration
# or: python scripts/test-integration.py
```

All tests are designed to run against a **local** instance spun up by `setup.sh`.

## Adding a New Job Type

Job types are Docker images that the worker pulls and runs. To add one:

### 1. Create the Docker Template

Create a new directory under `docker-jobs/examples/`:

```
docker-jobs/examples/
├── my-new-job/
│   ├── Dockerfile
│   └── entrypoint.sh
```

### 2. Inherit from the Base Image

```dockerfile
# docker-jobs/examples/my-new-job/Dockerfile
FROM computeswarm/base:latest

# Install job-specific dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    my-dependency \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /job
COPY entrypoint.sh /job/
RUN chmod +x /job/entrypoint.sh

ENTRYPOINT ["/job/entrypoint.sh"]
```

### 3. Write the Entrypoint Script

Your `entrypoint.sh` should:
- Read the job manifest from `/job/manifest.json` (injected by the worker at runtime).
- Execute the simulation.
- Write results to `/job/output/`.
- Write logs to `/job/output/job.log`.
- Exit with code `0` on success, non-zero on failure.

Example:

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "[my-new-job] Starting job..."

# Read input parameters from manifest
input_file=$(jq -r '.inputs.data_file' /job/manifest.json)
param=$(jq -r '.parameters.my_param' /job/manifest.json)

# Run the simulation
my-simulator --input "$input_file" --param "$param" --output /job/output/result.json

# Optional: copy input data alongside output for provenance
cp "$input_file" /job/output/

echo "[my-new-job] Done."
```

### 4. Register the Image in the Orchestrator

Update the orchestrator's job metadata or UI so researchers can select your new job type. This usually involves adding a record to the database or a config file (check `backend/app/models.py` and `backend/app/api/jobs.py` for the current schema).

### 5. Build and Test

```bash
make build-jobs
# or manually:
docker build -t computeswarm/my-new-job:latest docker-jobs/examples/my-new-job/
```

Submit a test job via the API or dashboard and verify the worker pulls, runs, and uploads the results correctly.

## Code Style

We follow standard conventions for each language. While CI linting is not yet wired up, please adhere to the following:

### Python (Backend & Worker)

- **Formatter**: [Black](https://black.readthedocs.io/) (`black backend/ worker/`)
- **Linter**: [Flake8](https://flake8.pycqa.org/) (`flake8 backend/ worker/`)
- **Line length**: 88 characters (Black default)
- **Docstrings**: Google-style or PEP 257

### JavaScript / TypeScript (Dashboard)

- **Formatter**: [Prettier](https://prettier.io/) (`cd dashboard && npm run format`)
- **Linter**: [ESLint](https://eslint.org/) (`cd dashboard && npm run lint`)
- Follow the existing React + Vite patterns in `dashboard/src/`

### General

- Keep commits focused and atomic.
- Write meaningful commit messages (imperative mood, e.g., "Add support for XYZ job type").
- Open a Pull Request with a clear description of changes and testing steps.
- CI placeholders are in `.github/workflows/ci.yml` — please ensure new code passes existing tests and does not break the build.

## Questions?

- Open a GitHub issue for bugs or feature requests.
- Check **[ARCHITECTURE.md](ARCHITECTURE.md)** for system design details.
- Review the **[README.md](README.md)** for quick-start commands.

Happy computing! 🧬⚛️🎨
