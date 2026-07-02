# ComputeSwarm — Distributed Scientific Compute Platform

ComputeSwarm is a modern, open-source distributed computing platform where researchers submit containerized scientific simulation jobs (physics, molecular docking, rendering) and volunteer workers run them on idle CPU/GPU hardware. The platform handles scheduling, result validation, real-time monitoring, credit-based billing, and admin oversight.

## Quick Start

Get the platform running locally in three commands:

```bash
# 1. Clone the repository
git clone https://github.com/your-org/compute-swarm.git
cd compute-swarm

# 2. Run the setup script (Linux/macOS/Git Bash)
./scripts/setup.sh

# 3. Start development services
./scripts/dev-start.sh
```

**Windows users**: Use PowerShell instead:

```powershell
.\scripts\setup.ps1
.\scripts\dev-start.ps1
```

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker Desktop | 4.25+ | Containers (PostgreSQL, Redis, MinIO, job images) |
| Docker Compose | v2 | Orchestration |
| Python | 3.10+ | Backend API & worker client |
| Node.js | 18+ | Dashboard (Vite + React) |
| Git | 2.40+ | Clone & Git Bash (Windows) |

**Windows notes:**
- Install [Git for Windows](https://git-scm.com/download/win) to get Git Bash.
- Enable WSL2 backend in Docker Desktop for best performance.
- Run Bash scripts in **Git Bash**, not PowerShell.
- Run PowerShell scripts (`.ps1`) in a PowerShell window with execution policy enabled: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`.

---

## Development Mode

After running `./scripts/setup.sh`, open **four separate terminals** and run:

### Terminal 1 — Infrastructure (already running after setup)

```bash
docker compose up -d db redis minio
```

*(This was already started by `setup.sh`, but you can re-run it if services stop.)*

### Terminal 2 — API Server

```bash
cd backend
source venv/bin/activate        # Git Bash / Linux / macOS
# OR .\venv\Scripts\Activate.ps1  # Windows PowerShell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs will be available at: **http://localhost:8000/docs**

### Seed Demo Data (Optional)

```bash
cd backend
python scripts/seed.py
```

This creates a demo researcher (`demo@example.com` / `demo123`), a demo worker, and a completed demo job so you can explore the dashboard immediately.

---

### Terminal 3 — Worker Client

```bash
cd worker
pip install -r requirements.txt
python -m src.main --register
```

### Terminal 4 — Dashboard

```bash
cd dashboard
npm install
npm run dev
```

Dashboard will be available at: **http://localhost:5173**

---

## Running Tests

```bash
# Quick smoke test (fast, checks API + basic job flow)
make test-smoke

# End-to-end test (full round-trip: submit → run → validate → download)
make test-e2e

# Integration test (infrastructure + API + database + storage)
make test-integration
```

Or run the test scripts directly:

```bash
python scripts/test-smoke.py
python scripts/test-e2e.py
python scripts/test-integration.py
```

---

## Architecture Overview

```
┌─────────────────────┐       ┌─────────────────────┐
│  Researcher         │──────▶│  React Dashboard      │
│  (Browser)          │       │  (Vite + Tailwind)    │
└─────────────────────┘       └──────────┬────────────┘
                                         │ HTTPS / WS
┌────────────────────────────────────────▼────────────────────┐
│  Orchestrator API (FastAPI)                                  │
│  • REST: jobs, workers, auth, results, billing               │
│  • WebSocket: real-time job status + worker heartbeats       │
│  • Celery + Redis: task queue & scheduling                   │
│  • PostgreSQL: jobs, users, results, billing                │
│  • MinIO: S3-compatible object storage (inputs & outputs)     │
└────────────────────────────────────────┬────────────────────┘
                                         │
┌────────────────────────────────────────▼────────────────────┐
│  Worker Client (Python desktop app)                        │
│  • Auto-registers with orchestrator                         │
│  • Pulls Docker images, runs jobs, uploads results           │
│  • CPU/GPU resource monitoring & idle detection              │
└─────────────────────────────────────────────────────────────┘
```

For full design details, see **[ARCHITECTURE.md](ARCHITECTURE.md)**.

---

## Project Structure

```
compute-swarm/
├── backend/              # FastAPI orchestrator API
│   ├── app/              # Core application (routes, models, services)
│   │   ├── api/          # REST routers (auth, jobs, workers, billing, admin)
│   │   ├── core/         # Business logic (scheduler, storage, email stubs)
│   │   ├── db/           # Database engine & session management
│   │   ├── templates/    # Email templates
│   │   └── models.py     # SQLAlchemy models
│   ├── alembic/          # Database migrations
│   ├── scripts/          # Seed data, helpers
│   ├── venv/             # Python virtual environment (created by setup)
│   ├── requirements.txt
│   └── Dockerfile
├── worker/               # Python desktop worker client
│   ├── src/              # Client, Docker runner, config
│   ├── requirements.txt
│   └── Dockerfile
├── dashboard/            # React + Vite researcher dashboard
│   ├── src/              # Components, API hooks, context
│   ├── package.json
│   └── Dockerfile
├── docker-jobs/          # Docker image templates for job types
│   ├── base/             # Base image shared by all jobs
│   └── examples/         # physics-sim, blender-render, molecular-dock
├── scripts/              # Setup, dev-start, test, deploy, and init helpers
├── .github/workflows/    # CI/CD stubs (ci.yml, deploy.yml)
├── docker-compose.yml    # Full-stack local orchestration
├── Makefile              # Common commands (dev, test, build, clean)
├── .env.example          # Environment variable template
├── VERSION               # Current release version
├── CHANGELOG.md          # Release history
└── README.md             # This file
```

---

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make setup` | Run the full setup script (`scripts/setup.sh`) |
| `make setup-win` | Run the Windows PowerShell setup script |
| `make dev` | Start infrastructure and print dev commands |
| `make up` | Start all Docker services (production-like) |
| `make down` | Stop all Docker services |
| `make build-jobs` | Build all Docker job images |
| `make test-smoke` | Run smoke tests |
| `make test-e2e` | Run end-to-end tests |
| `make test-integration` | Run integration tests |
| `make migrate` | Run Alembic migrations inside the API container |
| `make logs` | Tail Docker Compose logs |
| `make clean` | Stop containers and remove volumes + local images |
| `make seed` | Seed the database with demo data (user, worker, job) |
| `make lint` | *(Placeholder)* Run linters |
| `make format` | *(Placeholder)* Run formatters |

---

## Configuration

All runtime configuration is driven by environment variables. Copy `.env.example` to `.env` and adjust as needed:

```bash
cp .env.example .env
```

Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://computeswarm:changeme@db:5432/computeswarm` | PostgreSQL connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `MINIO_ENDPOINT` | `minio:9000` | MinIO S3 endpoint |
| `MINIO_ROOT_USER` | `minioadmin` | MinIO admin user |
| `MINIO_ROOT_PASSWORD` | `minioadmin` | MinIO admin password |
| `SECRET_KEY` | `change-me-in-production` | JWT signing secret — **change in production!** |
| `STRIPE_SECRET_KEY` | *(optional)* | Stripe integration for credit billing |

---

## Production Deployment

### Prerequisites

| Requirement | Details |
|-------------|---------|
| VPS | 2+ vCPU, 4 GB RAM, 40 GB SSD (minimum) |
| OS | Ubuntu 22.04 LTS or Debian 12 recommended |
| Docker | Docker Engine 24+ with Docker Compose plugin v2+ |
| Domain | A registered domain name with DNS A records |
| DNS | `api.yourdomain.com` → VPS IP, `app.yourdomain.com` → VPS IP |
| Firewall | Ports 80 and 443 open; 22 restricted to your IP |

### Step 1 — Configure Environment

```bash
# On your VPS, clone the repository
git clone https://github.com/your-org/compute-swarm.git
cd compute-swarm

# Create production env from template
cp .env.prod.example .env.prod

# Generate strong secrets
python scripts/generate-secrets.py --env-file .env.prod

# Edit domains and Stripe keys
nano .env.prod
```

Set these critical values in `.env.prod`:
- `API_DOMAIN` (e.g., `api.yourdomain.com`)
- `APP_DOMAIN` (e.g., `app.yourdomain.com`)
- `LETSENCRYPT_EMAIL` (a real, monitored email)
- `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` (live keys)
- `DATABASE_URL` (must match the generated `DB_PASSWORD`)
- `CORS_ORIGINS` (e.g., `https://app.yourdomain.com`)

### Step 2 — Run the Deploy Script

```bash
# Make scripts executable and deploy
chmod +x scripts/deploy.sh scripts/backup-db.sh scripts/health-check.sh
./scripts/deploy.sh
```

The script will:
1. Build/pull Docker images
2. Start infrastructure (PostgreSQL, Redis, MinIO)
3. Run Alembic database migrations
4. Start the API, Dashboard, Worker, and Traefik

### Step 3 — Verify SSL

```bash
curl -fsS https://api.yourdomain.com/health | python -m json.tool
curl -fsS https://app.yourdomain.com
```

Both should return valid HTTPS responses. Traefik will automatically request and renew Let's Encrypt certificates.

### Step 4 — Create First Admin User

```bash
docker compose -f docker-compose.prod.yml exec api \
    python scripts/create_admin.py admin@yourdomain.com 'YourSecureP@ss!'
```

Log in to the dashboard at `https://app.yourdomain.com` with the admin credentials.

### Step 5 — Seed Demo Data (Optional)

```bash
docker compose -f docker-compose.prod.yml exec api \
    python scripts/seed.py
```

Use the demo researcher account (`demo@computeswarm.local` / `demo123`) to test job submission and worker claims.

---

## Scaling

### Horizontal Scaling

**Add more worker nodes:**
- Install Docker on a new machine (or VM).
- Copy the worker directory and build the worker image.
- Run the worker container pointing to the public API:
  ```bash
  docker run -d --privileged -v /var/run/docker.sock:/var/run/docker.sock \
    -e ORCHESTRATOR_URL=https://api.yourdomain.com \
    computeswarm-worker:latest
  ```
- Workers auto-register with a unique API key on first startup.

**Add API replicas:**
- Update `docker-compose.prod.yml` to use a Docker Swarm stack or Kubernetes.
- Scale the `api` service to multiple replicas behind Traefik's load balancer.
- Use a managed PostgreSQL read replica for heavy read workloads.

### Vertical Scaling

- **VPS upgrade**: Increase CPU/RAM on the host. Update `deploy.resources.limits` in `docker-compose.prod.yml`.
- **Redis Cluster**: Replace the single Redis container with a Redis Cluster or managed Redis (AWS ElastiCache, Upstash) for higher throughput.
- **PostgreSQL read replicas**: Offload analytics and worker-list queries to read replicas.
- **MinIO distributed mode**: Run MinIO in distributed mode across multiple drives/nodes for higher object storage throughput.

### Monitoring at Scale

- **Prometheus + Grafana**: Scrape `https://api.yourdomain.com/metrics` every 15s.
- **Alertmanager**: Alert on error-rate spikes, worker count drops, or disk-full conditions.
- **Log aggregation**: Enable the commented `loki` service in `docker-compose.prod.yml` and ship Docker logs to Grafana Loki or a cloud provider (CloudWatch, Datadog, etc.).

---

## Contributing

We welcome contributions! See **[CONTRIBUTING.md](CONTRIBUTING.md)** for:

- Setting up your dev environment
- Running tests
- Adding new job types (Docker templates)
- Code style guidelines

For bug reports or feature requests, please open a GitHub issue.

---

## License

MIT License — see `LICENSE` for details.
