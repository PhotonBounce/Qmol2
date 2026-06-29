# Stage 2: Celery Distributed Task Queue — Execution Plan

## Stage 1: Core Celery Infrastructure
- [ ] Update `requirements.txt` (add celery, flower)
- [ ] Create `src/celery_app.py` (Celery app config with Redis broker/backend)
- [ ] Add sync Redis client to `src/redis_client.py`
- [ ] Create `src/tasks.py` (all 7 Celery task definitions)

## Stage 2: Backend Integration
- [ ] Rewrite `src/jobs.py` (Celery integration, SQLite+PostgreSQL dual mode)
- [ ] Update `src/cache.py` (Redis fallback layer)
- [ ] Update `src/ratelimit.py` (Redis fallback layer)

## Stage 3: API Endpoints
- [ ] Update `api.py` job endpoints (POST, GET, result, stream, cancel)

## Stage 4: Deployment & Config
- [ ] Update `docker-compose.yml` (worker + flower services)
- [ ] Update `Dockerfile` (comment about CMD override for worker)
- [ ] Update `.env.example` (Celery/Redis env vars)

## Quality Gates
- [ ] Every task is idempotent (safe to retry)
- [ ] SQLite fallback works when `USE_POSTGRES=false`
- [ ] Redis failures gracefully fall back to in-memory implementations
- [ ] SSE endpoint closes cleanly when job finishes or client disconnects
- [ ] `start_worker()` emits deprecation warning and no-ops
- [ ] `run_pending_sync()` still works for tests (calls Celery synchronously)
