# Q-Mol Improvement Plan

**Branch:** `claude/epic-mendel-a7r40z`  
**Goal:** Transform Q-Mol from a solo-built SQLite prototype into a production-grade, horizontally scalable molecular informatics platform with ML predictions, quantum chemistry, and enterprise SaaS features.

---

## Architecture Overview (Target State)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React SPA     │     │   Flutter App   │     │   CLI / SDKs    │
│   (dashboard)   │     │   (mobile)      │     │   (Python/TS/R) │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │ HTTPS / WSS
                    ┌────────────▼────────────┐
                    │  Cloudflare CDN / WAF   │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   K8s Ingress (Nginx)   │
                    └────────────┬────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
  ┌──────▼──────┐        ┌──────▼──────┐        ┌──────▼──────┐
  │ API Pod #1  │        │ API Pod #2  │        │ API Pod #N  │
  │  FastAPI    │        │  FastAPI    │        │  FastAPI    │
  │  + Uvicorn  │        │  + Uvicorn  │        │  + Uvicorn  │
  └──────┬──────┘        └──────┬──────┘        └──────┬──────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │      PostgreSQL         │
                    │   (primary + replica)   │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │        Redis            │
                    │  (cache / rate / queue)   │
                    └────────────┬────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
  ┌──────▼──────┐        ┌──────▼──────┐        ┌──────▼──────┐
  │ Celery      │        │ Celery      │        │ Celery      │
  │ Worker #1   │        │ Worker #2   │        │ Worker #N   │
  │ (RDKit)     │        │ (ML/ONNX)   │        │ (Quantum)   │
  └─────────────┘        └─────────────┘        └─────────────┘
```

---

## Stage 1: Database & Infrastructure (Week 1)

**Goal:** Replace SQLite with PostgreSQL + Redis, add Alembic migrations, and keep SQLite as a fallback dev mode.

### Deliverables

1. **`requirements.txt` additions**
   - `asyncpg>=0.29`
   - `sqlalchemy[asyncio]>=2.0`
   - `alembic>=1.13`
   - `redis>=5.0`
   - `psycopg2-binary>=2.9` (for sync worker fallback)

2. **`config.py` updates**
   - Add `DATABASE_URL`, `REDIS_URL`, `USE_POSTGRES` env vars
   - Keep SQLite paths as fallback when `USE_POSTGRES=false`

3. **`src/db.py`** — SQLAlchemy 2.0 async setup
   - `AsyncEngine` with connection pooling
   - `async_sessionmaker` factory
   - `get_db_session()` dependency for FastAPI

4. **`src/models.py`** — SQLAlchemy ORM models
   - `Molecule` (mirrors `storage.py` schema)
   - `ApiKey` (mirrors `keys.py` schema)
   - `Usage` (mirrors `keys.py` usage table)
   - `Team`, `TeamMember` (mirrors `teams.py`)
   - `Job` (mirrors `jobs.py`)
   - `AuditLog` (mirrors `audit.py`)
   - `Coupon`, `Referral`, `Invoice` (billing tables)

5. **`alembic/`** — Migration setup
   - `alembic.ini` configured for async PostgreSQL
   - `env.py` with `asyncpg` URL parsing
   - Initial migration: `migrations/versions/001_initial_schema.py`

6. **`src/redis_client.py`** — Redis connection pool
   - `redis_pool` singleton
   - Helper functions: `get_redis()`, `cache_get()`, `cache_set()`, `rate_limit_check()`

7. **`scripts/migrate_sqlite_to_postgres.py`** — One-time migration script
   - Reads SQLite `qmol.sqlite`, `keys.sqlite`, `jobs.sqlite`
   - Writes to PostgreSQL with batch inserts
   - Handles `state.json` resume cursor

8. **`docker-compose.yml` update**
   - Add `postgres:15-alpine` service
   - Add `redis:7-alpine` service
   - Update `qmol` service with new env vars and healthchecks

### Validation Criteria
- [ ] `pytest` passes against PostgreSQL (using testcontainers)
- [ ] `docker-compose up` brings up API + Postgres + Redis successfully
- [ ] `/health` endpoint returns DB + Redis connectivity status
- [ ] SQLite fallback mode still works when `USE_POSTGRES=false`

---

## Stage 2: Async Job Queue (Week 1–2)

**Goal:** Replace crude SQLite job polling with a proper distributed task queue.

### Deliverables

1. **Celery setup** (recommended over Arq for ecosystem maturity)
   - `src/celery_app.py` — Celery app with Redis broker
   - `src/tasks.py` — Task definitions:
     - `compute_batch_task(smiles_list, job_id, api_key)`
     - `predict_batch_task(smiles_list, job_id, api_key)`
     - `screen_batch_task(smiles_list, job_id, api_key)`
     - `similarity_search_task(query_smiles, top_k, job_id)`
     - `cluster_task(smiles_list, cutoff, job_id)`
     - `conformer_generation_task(smiles, n_conformers, job_id)`
     - `publish_snapshot_task()` (worker background task)

2. **API endpoints update**
   - `POST /v1/jobs` — enqueue task, return `job_id`
   - `GET /v1/jobs/{job_id}` — query Celery result backend
   - `GET /v1/jobs/{job_id}/stream` — Server-Sent Events for real-time progress
   - `DELETE /v1/jobs/{job_id}` — revoke task if still pending

3. **Result backend**
   - Use Redis for task metadata + PostgreSQL for result storage
   - Large results (Parquet, SDF) stored in S3-compatible object storage with presigned URLs

4. **Worker deployment**
   - `Dockerfile.worker` — separate image for Celery workers
   - `docker-compose.yml` — `worker` service with CPU affinity for RDKit
   - Kubernetes `Deployment` with HPA based on queue depth

### Validation Criteria
- [ ] Submit 50k SMILES batch → job queued → worker processes → result available via SSE
- [ ] Worker container can be scaled independently from API containers
- [ ] Failed jobs retry with exponential backoff (max 3 retries)
- [ ] Job progress is streamable in real-time

---

## Stage 3: API v2 (Week 2–3)

**Goal:** Modernize the API with versioning, Pydantic v2, OpenAPI 3.1, and auto-generated SDKs.

### Deliverables

1. **Router restructuring**
   ```
   src/routers/
   ├── __init__.py
   ├── v1/
   │   ├── __init__.py
   │   ├── compute.py
   │   ├── descriptors.py
   │   ├── similarity.py
   │   ├── screen.py
   │   ├── predict.py
   │   ├── jobs.py
   │   ├── admin.py
   │   ├── billing.py
   │   └── health.py
   └── v2/  (future)
   ```

2. **Pydantic v2 models**
   - All request/response schemas use `BaseModel` with `ConfigDict`
   - `field_validator` for SMILES validation (RDKit parse check)
   - `computed_field` for derived properties
   - Rich OpenAPI examples on every model

3. **Middleware improvements**
   - `X-Request-ID` propagation (UUID4 per request)
   - `GZipMiddleware` for responses > 1KB
   - `TrustedHostMiddleware` (when behind CDN)
   - Structured request logging with `structlog`

4. **SDK generation pipeline**
   - `.github/workflows/sdk-publish.yml`
   - Auto-generate Python, TypeScript, R clients from OpenAPI spec
   - Publish to PyPI, npm, CRAN on every release

5. **Deprecation strategy**
   - `/compute` remains at root for backward compatibility (redirects to `/v1/compute`)
   - `Sunset` header on legacy routes
   - 6-month deprecation window before `/v2/` becomes default

### Validation Criteria
- [ ] All existing tests pass against `/v1/` routes
- [ ] OpenAPI spec validates with `swagger-codegen` without warnings
- [ ] Python SDK generated and installable via `pip install qmol-client`
- [ ] Load test: 1000 RPS on `/v1/compute` with <50ms p99 latency

---

## Stage 4: ML Property Prediction (Week 3–4)

**Goal:** Replace heuristic ADMET predictions with ONNX neural network models.

### Deliverables

1. **Model serving architecture**
   - `src/ml/` package:
     - `onnx_predictor.py` — ONNX Runtime wrapper
     - `features.py` — RDKit → model input vector conversion (Morgan fingerprints, descriptors)
     - `models/` — Pre-trained ONNX models (checked into Git LFS or downloaded from HuggingFace)
   - Models served in-process (FastAPI) for latency; Triton server as upgrade path

2. **Models to ship**
   | Property | Model | Source |
   |----------|-------|--------|
   | Aqueous solubility (logS) | ESOL + Chemprop ensemble | MoleculeNet |
   | Blood-brain barrier (BBB) | Graph neural network | MoleculeNet |
   | hERG inhibition | RNN-hERG | DeepDL |
   | CYP450 1A2/2C9/2D6/3A4 | Multi-task DNN | MoleculeNet |
   | Human plasma protein binding | Random Forest | MoleculeNet |
   | Ames mutagenicity | GraphConv | MoleculeNet |
   | Synthetic accessibility | SAscore (existing) | RDKit |

3. **New endpoints**
   - `POST /v1/predict/ml` — Full ML panel (charge: 5× per molecule)
   - `POST /v1/predict/{property}` — Single property endpoint
   - `GET /v1/models` — List available models with accuracy metrics
   - `GET /v1/models/{model_id}/info` — Model card (training data, R², coverage)

4. **Confidence intervals**
   - Every prediction returns `value`, `unit`, `confidence_score` (0–1), `applicability_domain` (in/out)
   - Models flag out-of-domain molecules (structural similarity to training set)

### Validation Criteria
- [ ] R² > 0.80 on held-out test set for logS, BBB, hERG
- [ ] Prediction latency < 100ms per molecule (in-process ONNX)
- [ ] Model cards display accurate training provenance
- [ ] Out-of-domain flagging works on novel scaffolds

---

## Stage 5: React Dashboard (Week 4–5)

**Goal:** Replace static HTML with a modern, interactive SPA.

### Deliverables

1. **`dashboard/`** — React 18 + TypeScript + Vite project
   - **Tech stack:** React 18, TanStack Query, TanStack Table, React Router, MUI/shadcn, Plotly, 3Dmol.js
   - **Pages:**
     - `/app` — Main workspace: SMILES input, batch upload, results grid, export
     - `/app/jobs` — Job queue monitor with real-time SSE progress bars
     - `/app/usage` — Quota meter, usage history, invoice list
     - `/app/teams` — Member management, quota sharing, role assignments
     - `/app/molecule/{id}` — Full property card, 2D/3D viewer, similarity network
     - `/app/admin` — Key provisioning, revenue chart, health status, metrics
   - **Features:**
     - Drag-drop CSV/SDF upload
     - Molecule sketcher (Ketcher integration)
     - Real-time job progress via SSE
     - Dark mode toggle
     - Responsive mobile layout

2. **Integration**
   - Stripe Checkout embedded for in-app upgrades
   - API key management (show, rotate, copy)
   - Team invitation flow (email + magic link)

3. **Build & deploy**
   - `dashboard/Dockerfile` — Nginx serving static build
   - GitHub Actions: build → deploy to Cloudflare Pages / Vercel
   - Environment-based API base URL (`https://api.qmol.app` vs `http://localhost:8000`)

### Validation Criteria
- [ ] Dashboard loads in < 2 seconds (Lighthouse performance > 90)
- [ ] 50k SMILES batch upload queues successfully via UI
- [ ] 3D viewer renders correctly for arbitrary SMILES
- [ ] Mobile layout is usable (not just desktop scaled down)

---

## Stage 6: Quantum VQE Implementation (Week 5–6)

**Goal:** Fulfill the "quantum-verified" brand promise with a real VQE tier.

### Deliverables

1. **`src/quantum/`** package
   - `vqe_qiskit.py` — Qiskit Nature VQE implementation
   - `vqe_pyqpanda.py` — pyQPanda fallback
   - `provenance.py` — Quantum circuit hashing, certificate generation
   - `cloud.py` — IBM Quantum / AWS Braket cloud job submission

2. **Implementation details**
   - Use `qiskit-nature` + `PySCFDriver` for molecular Hamiltonian
   - `UCCSD` ansatz with `SLSQP` optimizer
   - Jordan-Wigner or Parity mapper for fermion → qubit
   - Fallback to classical CCSD when qubit count exceeds budget
   - Store circuit hash + execution timestamp as quantum provenance certificate

3. **New endpoints**
   - `POST /v1/compute/quantum` — Quantum compute tier (charge: 50× per molecule)
   - `GET /v1/compute/quantum/{job_id}/certificate` — Download provenance certificate
   - `GET /v1/quantum/status` — IBM Quantum queue status / cloud availability

4. **Business integration**
   - "Quantum-certified" badge on dataset rows
   - Premium tier add-on: $500/month for quantum compute access
   - Partnership page with IBM Quantum / AWS Braket

### Validation Criteria
- [ ] VQE computes H₂ energy within 0.01 Ha of FCI reference
- [ ] Provenance certificate is verifiable (contains circuit hash, job ID, timestamp)
- [ ] Cloud fallback works when IBM Quantum queue is > 1 hour
- [ ] Classical CCSD still runs as ground truth for validation

---

## Stage 7: K8s / Helm / Observability (Week 6–7)

**Goal:** Production-grade deployment with monitoring, logging, and autoscaling.

### Deliverables

1. **`helm/qmol/`** — Helm chart
   - `values.yaml` with configurable replicas, resources, autoscaling
   - `templates/api-deployment.yaml` — FastAPI pods
   - `templates/worker-deployment.yaml` — Celery worker pods
   - `templates/ingress.yaml` — Nginx ingress with TLS
   - `templates/postgres.yaml` — Bitnami PostgreSQL subchart
   - `templates/redis.yaml` — Bitnami Redis subchart
   - `templates/service-monitor.yaml` — Prometheus ServiceMonitor

2. **Observability stack**
   - **Prometheus** + **Grafana** — Metrics dashboards (request latency, queue depth, DB connections, GPU utilization)
   - **Loki** — Centralized log aggregation with structured JSON logs
   - **Sentry** — Error tracking and performance monitoring
   - **OpenTelemetry** — Distributed tracing across API → DB → Cache → Worker

3. **CI/CD improvements**
   - Multi-arch Docker builds (`linux/amd64`, `linux/arm64`)
   - Security scanning (Trivy, Bandit, Safety)
   - Type checking (`pyright` or `mypy --strict`)
   - Linting (`ruff`)
   - Semantic release (auto-version bump from conventional commits)
   - Pre-commit hooks

4. **Disaster recovery**
   - PostgreSQL: WAL archiving to S3, daily `pg_dump`
   - Redis: AOF persistence + Sentinel for HA
   - RPO < 1 hour, RTO < 4 hours

### Validation Criteria
- [ ] `helm install qmol ./helm/qmol` deploys full stack in < 5 minutes
- [ ] HPA scales API pods from 2 → 10 under synthetic load
- [ ] Grafana dashboard shows real-time metrics
- [ ] `helm test` passes smoke tests against deployed stack

---

## Stage 8: Mobile & Ecosystem (Week 7–8)

**Goal:** Complete the Flutter app and expand the ecosystem.

### Deliverables

1. **Flutter app completion**
   - `mobile/lib/` — Full Dart implementation:
     - SMILES input (text + camera OCR for chemical structures)
     - Batch processing (CSV upload from phone storage)
     - Offline mode (cache results, queue jobs when reconnecting)
     - In-app purchases (Google Play / Apple App Store tiers)
     - Push notifications (job completion via Firebase)
     - Molecule sketcher (Ketcher web view)
   - CI: `flutter build apk` and `flutter build ios` in GitHub Actions

2. **SDK expansion**
   - `qmol-python` — Already have `qmol_client.py`; make it pip-installable
   - `qmol-typescript` — For React dashboard and Node.js integrations
   - `qmol-r` — For bioinformatics researchers (bioconductor-style)
   - `qmol-java` — For enterprise pharma stacks (Maven Central)

3. **Data marketplace**
   - AWS Data Exchange listing (auto-updated via API)
   - Custom model training service for enterprise clients
   - Patent / literature prior-art search endpoint (`/v1/prior-art`)

### Validation Criteria
- [ ] Flutter app runs on Android + iOS simulators
- [ ] In-app purchase flows through Google Play test sandbox
- [ ] Python SDK installable via `pip install qmol-client`
- [ ] AWS Data Exchange product auto-updates on snapshot

---

## Cross-Cutting Concerns

### Security & Compliance
- API keys hashed with `bcrypt` (not plaintext)
- `DELETE /v1/account` — GDPR right to erasure
- TLS 1.3 everywhere
- SOC 2 Type II readiness checklist
- `security.txt` and vulnerability disclosure policy

### Performance Budgets
- API p99 latency: < 100ms for single-molecule endpoints
- API p99 latency: < 5s for batch endpoints (queuing response)
- Worker throughput: > 100 molecules/minute (RDKit tier), > 10/minute (ML tier)
- Dashboard TTI: < 2 seconds
- Mobile cold start: < 3 seconds

### Testing Strategy
- **Unit:** pytest with SQLite `:memory:` (fast, isolated)
- **Integration:** testcontainers for PostgreSQL + Redis
- **Load:** Locust / k6 at 2× expected peak traffic
- **Chaos:** Randomly kill API pods and verify graceful degradation

---

## Dependency Graph

```
Stage 1 (DB + Redis)
       │
       ├────── Stage 2 (Job Queue) ──────┐
       │                                   │
       ├────── Stage 3 (API v2) ─────────┤
       │                                   │
       │         Stage 4 (ML) ─────────────┤
       │                                   │
       │         Stage 5 (Dashboard) ──────┤
       │                                   │
       │         Stage 6 (Quantum) ────────┤
       │                                   │
       │         Stage 7 (K8s) ────────────┘
       │
       └────── Stage 8 (Mobile + Ecosystem)
```

Stages 2–6 depend on Stage 1. Stage 7 depends on all previous stages. Stage 8 is largely independent.

---

## Execution Checklist

- [ ] Stage 1: Database & Infrastructure
- [ ] Stage 2: Async Job Queue
- [ ] Stage 3: API v2
- [ ] Stage 4: ML Property Prediction
- [ ] Stage 5: React Dashboard
- [ ] Stage 6: Quantum VQE
- [ ] Stage 7: K8s / Helm / Observability
- [ ] Stage 8: Mobile & Ecosystem
