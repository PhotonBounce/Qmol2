# ComputeSwarm — Distributed Scientific Compute Platform

## Overview
A distributed computing platform where researchers submit containerized simulation jobs, volunteer workers run them on idle hardware (CPU/GPU), and the platform orchestrates scheduling, validation, and payments.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    RESEARCHER DASHBOARD                     │
│  (React + Vite — job submit, monitor, billing, download)    │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────────────────────┐
│              ORCHESTRATOR API (FastAPI)                     │
│  - REST API: jobs, workers, auth, results, billing          │
│  - WebSocket: real-time job status, worker heartbeats       │
│  - Scheduler: Redis-backed Celery queue, job dispatch       │
│  - Validator: redundant execution, result verification      │
│  - Auth: JWT tokens (researchers + workers)                 │
└────────┬─────────────────────────────┬──────────────────────┘
         │                             │
         │ PostgreSQL                  │ Redis
┌────────▼────────┐          ┌────────▼────────┐
│   Jobs DB         │          │   Celery Queue    │
│   Workers DB      │          │   Real-time PubSub│
│   Results DB      │          │   Cache           │
│   Billing DB      │          │   WebSocket State │
└───────────────────┘          └───────────────────┘
         ▲
         │ WebSocket / HTTP
┌────────┴────────────────────────────────────────────────────┐
│              WORKER CLIENT (Python Desktop App)             │
│  - Auto-registers with orchestrator                        │
│  - Downloads job manifests + Docker images                  │
│  - Runs Docker containers (CPU/GPU-limited)                  │
│  - Uploads results + logs                                     │
│  - Idle detection (optional)                                │
│  - Earns credits per completed work unit                    │
└─────────────────────────────────────────────────────────────┘
```

## Core Entities

### Job
- `id`: UUID
- `user_id`: Foreign key (researcher)
- `name`: string
- `docker_image`: string (e.g., `computeswarm/blender-render:latest`)
- `command`: string (container CMD override)
- `env_vars`: JSON dict
- `input_files`: list of S3/MinIO URLs (tar.gz archive)
- `status`: `pending` | `assigned` | `running` | `completed` | `failed` | `validating`
- `work_unit_count`: int (number of units to split the job into)
- `reward_per_unit`: float (credits)
- `created_at`, `updated_at`
- **Relationship**: `work_units` → list of `WorkUnit` rows (no longer stored as JSON on the Job table)

### WorkUnit
- `id`: UUID
- `job_id`: UUID
- `unit_index`: int (which slice of the job)
- `status`: `pending` | `assigned` | `running` | `completed` | `failed` | `validated`
- `assigned_worker_id`: UUID (nullable)
- `input_artifact_url`: string (S3/MinIO)
- `result_artifact_url`: string (nullable)
- `result_checksum`: string (nullable, SHA-256)
- `started_at`, `completed_at`, `validated_at`
- `validation_replicas`: list of {worker_id, result_checksum, match: bool}

### Worker
- `id`: UUID
- `name`: string (user-defined or auto-generated)
- `api_key`: string (hashed, for authentication)
- `status`: `online` | `offline` | `busy` | `banned`
- `capabilities`: JSON (cpu_cores, ram_gb, gpu_model, cuda_version, os)
- `reputation_score`: float (0-1, based on valid result rate)
- `total_credits_earned`: float
- `pending_credits`: float
- `last_heartbeat`: datetime
- `created_at`

### User (Researcher)
- `id`: UUID
- `email`: string
- `hashed_password`: string
- `role`: `researcher` | `admin`
- `credits_balance`: float (buys with Stripe, spends on jobs)
- `stripe_customer_id`: string
- `created_at`

## API Design (Orchestrator)

### Auth
- `POST /auth/register` — email, password → JWT
- `POST /auth/login` — email, password → JWT
- `POST /auth/worker-register` — name, capabilities → worker_id, api_key
- `POST /auth/worker-refresh` — api_key → new api_key (rotation)

### Jobs (Researcher)
- `POST /jobs` — create job (docker_image, command, env_vars, input_files, work_unit_count, reward_per_unit) → job_id
  - Orchestrator splits job into N work units, uploads to S3/MinIO
- `GET /jobs` — list jobs with pagination
- `GET /jobs/{job_id}` — job details + work unit statuses
- `GET /jobs/{job_id}/results` — download aggregated results as tar.gz
- `POST /jobs/{job_id}/cancel` — cancel pending/unassigned units

### Workers (Orchestrator)
- `POST /workers/heartbeat` — worker_id, api_key, current_status, capabilities_snapshot → maybe receive a new job assignment
- `POST /workers/claim-unit` — worker_id, api_key → gets assigned a pending work unit with download URLs
- `POST /workers/submit-result` — work_unit_id, api_key, result_file (multipart), checksum, logs → marks unit completed
- `GET /workers/profile` — worker stats, credits earned, reputation

### Admin/Billing
- `POST /billing/checkout` — researcher buys credits via Stripe
- `GET /billing/balance` — current credits
- `POST /billing/withdraw` — worker requests payout (Stripe Connect, crypto, or manual)
- `GET /admin/stats` — aggregate stats (users, workers, jobs, credits)
- `GET /admin/workers` — list all workers (paginated)
- `POST /admin/workers/{id}/ban` — ban a worker
- `POST /admin/workers/{id}/unban` — unban a worker (sets offline)
- `GET /admin/jobs` — list all jobs (paginated)
- `GET /admin/users` — list all users (paginated)

### Email Notifications (MVP Stubs)
- `send_email(to, subject, body, html)` — logs to console; SMTP TODO
- `notify_job_completed(user_email, job_name)` — sent when a job finishes
- `notify_worker_banned(worker_email, reason)` — sent on ban action
- `notify_low_credits(user_email, balance)` — warning when balance is low

### WebSocket `/ws`
- Researchers subscribe to `job:{job_id}` channel for real-time status updates
- Workers maintain persistent connection for instant job pushes (optional, can use polling)

## Scheduler Logic (Celery Beat + Redis)

### Job Dispatch Cycle (every 5 seconds via Celery beat)
1. Query all `pending` work units with `assigned_worker_id IS NULL`
2. Query all `online` workers with `status != busy`
3. Match: worker capabilities must satisfy job requirements (CPU, RAM, GPU if needed)
4. Assign: set `assigned_worker_id`, status → `assigned`, push to Redis pubsub for worker
5. If worker fails to claim within 60 seconds, re-queue the unit

### Validation Cycle (every 30 seconds)
1. Query all `completed` work units not yet `validated`
2. For each: dispatch to 2 additional workers (different from original) as validation replicas
3. Compare SHA-256 checksums of all 3 results
4. If majority match: mark `validated`, reward original worker + validators
5. If no majority match: flag as failed, re-queue, adjust worker reputation

### Worker Health Check (every 30 seconds)
1. Mark workers with `last_heartbeat < now - 120s` as `offline`
2. Re-queue any work units assigned to offline workers
3. If a worker has 3 failed validations in a row, set `status = banned`

## Worker Client Protocol

### Startup Flow
1. Read config file (`~/.computeswarm/config.json`) or CLI args
2. Register with orchestrator (if first run) or authenticate with existing API key
3. Send capabilities: CPU cores, RAM, GPU info, OS, Docker version
4. Enter main loop:
   - Heartbeat every 15 seconds (POST /workers/heartbeat)
   - Check for assigned work units
   - If assigned: download input artifact, run Docker, upload result, repeat

### Job Execution Flow
1. Receive work unit assignment: `{work_unit_id, job_id, docker_image, command, env_vars, input_artifact_url}`
2. Download input artifact to `~/.computeswarm/jobs/{work_unit_id}/input/`
3. Pull Docker image (if not cached)
4. Run container with:
   - CPU limit: configurable (default 80% of cores)
   - RAM limit: configurable (default 75% of available)
   - GPU passthrough if available (`--gpus all`)
   - Volume mount: input dir → `/workspace/input`, output dir → `/workspace/output`
   - Timeout: job-specific or default 1 hour
5. Capture stdout/stderr logs
6. Tar.gz the output directory
7. Upload result artifact to presigned S3/MinIO URL
8. Submit result + checksum + logs to orchestrator
9. Clean up local files

### Idle Detection (Optional)
- Monitor CPU/GPU usage. If below 10% for 5 minutes, consider worker available.
- User can set: `always_run`, `when_idle`, `scheduled_hours`

## Docker Job Specification

Every job runs inside a Docker container. The platform provides:
- A base image with common scientific tools (Python, NumPy, SciPy, OpenMPI, CUDA runtime)
- Input files mounted at `/workspace/input`
- Output MUST be written to `/workspace/output`
- The container is killed after timeout
- Exit code 0 = success, anything else = failure

### Example Job Types
1. **Blender Render**: `docker_image: computeswarm/blender`, command: `blender -b /workspace/input/scene.blend -o /workspace/output/frame_#### -f {FRAME_NUMBER}`
2. **Physics Simulation**: Custom Python + NumPy image, command: `python /workspace/input/sim.py --output /workspace/output/result.npy`
3. **Molecular Docking**: AutoDock Vina image, command: `vina --receptor /workspace/input/receptor.pdbqt --ligand /workspace/input/ligand.pdbqt --out /workspace/output/result.pdbqt`

## Storage
- **Object Storage**: MinIO (S3-compatible) for input/output artifacts. Each work unit gets a presigned URL for upload/download.
- **Database**: PostgreSQL for relational data (jobs, workers, users, billing).
- **Cache/Queue**: Redis for Celery, job dispatch pub/sub, and real-time WebSocket state.

## Security
- All worker→orchestrator communication over HTTPS
- Workers authenticate with API keys (not JWT, since they are long-lived)
- Researchers authenticate with JWT (short-lived, refresh token)
- Input/output artifacts use presigned URLs with expiration (15 min for download, 1 hour for upload)
- Docker containers run with no network access (`--network none`) unless explicitly requested
- Resource limits enforced via Docker cgroups

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI (Python 3.11) |
| Database | PostgreSQL 15 + SQLAlchemy 2.0 + Alembic |
| Queue/Cache | Redis 7 + Celery 5 |
| Object Storage | MinIO |
| Worker Client | Python 3.11 + Docker SDK + requests |
| Dashboard | React 18 + Vite + TailwindCSS + Recharts |
| Auth | PyJWT + bcrypt + python-jose |
| Payments | Stripe (Stripe Checkout + Stripe Connect) |
| Containerization | Docker + Docker Compose |
| Real-time | FastAPI WebSocket (native) or Socket.io |

## MVP Cut
- V1: No GPU scheduling, no Stripe payments (credits seeded manually), no WebSocket (use polling)
- V2: Add GPU detection, Stripe billing, WebSocket real-time updates
- V3: Add reputation-based validation weighting, validator marketplace, more job types

## File Naming Conventions
- Python: `snake_case.py`, functions `snake_case`, classes `PascalCase`
- React: `PascalCase.jsx`, components `PascalCase`
- DB tables: `snake_case`, models `PascalCase`
- API routes: `kebab-case`
- Environment variables: `UPPER_SNAKE_CASE`

## Environment Variables (`.env`)
```
# App
APP_ENV=development
SECRET_KEY=change-me-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=postgresql://computeswarm:changeme@db:5432/computeswarm

# Redis
REDIS_URL=redis://redis:6379/0

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=computeswarm
MINIO_USE_SSL=false

# Stripe (optional for V1)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Worker (client-side)
ORCHESTRATOR_URL=https://api.computeswarm.local
WORKER_API_KEY=...
MAX_CPU_PERCENT=80
MAX_RAM_PERCENT=75
```

---

## Production Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           INTERNET                                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
         ┌─────────────────┴─────────────────┐
         │         Traefik (SSL Termination)  │
         │  • HTTP → HTTPS redirect           │
         │  • Let's Encrypt auto-renewal      │
         │  • Rate limiting (100 req/min/IP)  │
         │  • Security headers (HSTS, XSS)    │
         └──────────┬──────────────────┬─────┘
                    │                  │
      api.yourdomain.com      app.yourdomain.com
                    │                  │
         ┌──────────▼────┐    ┌──────▼──────────┐
         │  FastAPI API   │    │  React Dashboard │
         │  • /health      │    │  (Nginx static)  │
         │  • /metrics    │    │  • /api/ proxy   │
         │  • Gunicorn    │    │    to backend    │
         │    + 4 workers │    └──────────────────┘
         └──────┬────────┘
                │
    ┌───────────┼───────────┐
    │           │           │
┌───▼───┐  ┌───▼───┐  ┌───▼────┐
│  PostgreSQL │  │  Redis  │  │  MinIO  │
│  (internal) │  │(internal)│  │(internal)│
└─────────────┘  └─────────┘  └─────────┘
         ▲
         │
┌────────┴─────────────────────────────────────┐
│  Worker Nodes (separate machines or local)   │
│  • Docker-in-Docker or rootless Docker        │
│  • Auto-register with API key                 │
└───────────────────────────────────────────────┘
```

### Internal Network
- All backend services (`db`, `redis`, `minio`, `api`) communicate over the dedicated `computeswarm-network` Docker bridge.
- **No database, Redis, or MinIO ports are exposed to the host** — they are only reachable inside the Docker network.
- The `worker` service (if running on the same host) is `privileged` and mounts the host Docker socket. For multi-host deployments, workers run on separate machines and connect via the public API domain.

### SSL Termination
- Traefik handles all TLS using Let's Encrypt (`TLS-ALPN-01` challenge).
- Certificates are stored in the `letsencrypt_data` Docker volume and persist across container restarts.
- HTTP requests on port 80 are automatically redirected to HTTPS on port 443.

### Database Backup Strategy
- **Automated**: `scripts/backup-db.sh` runs `pg_dump` via the Docker container to a timestamped gzip file.
- **Retention**: Old backups are automatically deleted after 7 days (configurable via `RETENTION_DAYS`).
- **Off-site**: Optional MinIO upload (`mc cp`) to a separate backup bucket.
- **Cron**: `0 3 * * * /opt/computeswarm/scripts/backup-db.sh` — daily at 03:00.

### Monitoring Stack
- **Prometheus metrics** exposed at `/metrics` on the API:
  - `compute_swarm_requests_total` (method, endpoint, status)
  - `compute_swarm_jobs_created_total`
  - `compute_swarm_work_units_completed_total`
  - `compute_swarm_workers_online`
  - `compute_swarm_request_duration_seconds`
- **Health endpoint**: `/health` returns JSON status of DB, Redis, and MinIO.
- **External uptime monitoring**: `scripts/health-check.sh` can be wired to UptimeRobot, Pingdom, or StatusCake.
- **Log aggregation**: Docker `json-file` driver with rotation (`max-size: 100m`, `max-file: 3`). Optional Loki/Fluentd integration commented in `docker-compose.prod.yml`.
