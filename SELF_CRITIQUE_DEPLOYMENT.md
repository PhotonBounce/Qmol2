# Q-Mol Deployment Self-Critique — BLOCKER REPORT

**Scope:** Brutal honest review of everything that will block deployment on free hosting (Render free tier, Railway hobby, Fly.io free, or self-hosted PC with 512 MB RAM).  
**Project:** `D:\Qmol-3` (Q-Mol FastAPI v2.0.0)  
**Date:** 2026-06-29  
**Reviewer:** Senior Engineering Manager (self-critique mode)

---

## Executive Summary

Q-Mol **will not start** on a clean machine without Redis, Celery, `asyncpg`, and `psycopg2-binary` installed, even when `USE_POSTGRES=false`. The root cause is an unconditional import chain from `api.py` → `v1_router` → `jobs_router` → `src.jobs` → `src.celery_app` (Celery) and `src.dependencies` → `src.redis_client` (Redis). This makes the "SQLite-only / no-infrastructure" promise in the README a lie.

In addition, the health-check path configured in `render.yaml` (`/health`) does **not** exist as a direct endpoint; it is caught by a legacy redirect middleware and returns `307`, which most free-tier platforms treat as **unhealthy**. The Dockerfile health check relies on `urllib.request` following redirects, which is brittle.

The app also ships with **dead-weight dependencies** (`scikit-learn`, `flower`, `apscheduler`, `kaggle`) that bloat the Docker image but are never imported by the API server, and **missing ONNX models** (3 out of 5) that silently degrade the `/predict/ml` endpoint without warning the caller.

**Bottom line:** This is not deployable on Render free, Railway, or a 512 MB VPS without code fixes.

---

## P0 — WILL NOT START

### 1. Redis is imported unconditionally at every router
**Severity:** P0  
**File:** `src/redis_client.py:6-7`, `src/dependencies.py:16`, `src/ratelimit.py:14`, `src/cache.py:20`, `src/jobs.py:22`, `src/tasks.py:20`  
**What:** `src/redis_client.py` does `import redis.asyncio as redis` and `import redis as redis_sync` at module level. `src/dependencies.py` imports `redis_client` unconditionally. Nearly every router in `src/routers/v1/` imports `src.dependencies` (auth, quotas, rate limits). Therefore, if `redis` is not installed, `ModuleNotFoundError` crashes startup before the first request is served.

**Impact:**
- Free-tier hosts that don’t provide Redis out of the box (e.g., Render free web service without a Redis add-on) are blocked.
- Self-hosted PC without a Redis server running is blocked *even if* the code never actually tries to connect to Redis.

**Fix:**
```python
# src/redis_client.py
from __future__ import annotations
try:
    import redis.asyncio as redis
    import redis as redis_sync
    HAS_REDIS = True
except ImportError:
    redis = None  # type: ignore
    redis_sync = None  # type: ignore
    HAS_REDIS = False
```
Then guard every function that returns a client:
```python
def get_redis() -> redis.Redis:
    if not HAS_REDIS:
        raise RuntimeError("redis package not installed")
    ...
```
In `src/dependencies.py`, only import `redis_client` inside the async functions that need it, or use a lazy import wrapper.

---

### 2. Celery is imported unconditionally at startup
**Severity:** P0  
**File:** `src/celery_app.py:3`, `src/jobs.py:21`, `src/routers/v1/jobs.py:10`  
**What:** `src/routers/v1/__init__.py` imports `jobs_router` at module level. `jobs_router` imports `src.jobs`, which imports `from src.celery_app import app`. `src.celery_app` imports `from celery import Celery`. If `celery` is not installed, the app fails to import.

**Impact:**
- Cannot run the API server on a machine without Celery, even if you never plan to submit a batch job.
- `flower` is also in `requirements.txt` but is only a CLI tool; it is dead weight.

**Fix:** Make `src/jobs.py` import Celery lazily, or create a `LazyCelery` wrapper:
```python
# src/jobs.py
_celery_app = None

def _get_celery_app():
    global _celery_app
    if _celery_app is None:
        from src.celery_app import app
        _celery_app = app
    return _celery_app
```
Only call `_get_celery_app()` inside `submit()` and `cancel()`, not at module load time.

---

### 3. `asyncpg` and `psycopg2-binary` are required in `pip install` even for SQLite-only mode
**Severity:** P0 (build / deployment time)  
**File:** `requirements.txt:25-29`  
**What:** `asyncpg>=0.29`, `psycopg2-binary>=2.9`, `alembic>=1.13` are listed as top-level requirements. When `USE_POSTGRES=false`, `src/db.py` never instantiates an engine and never touches these packages. However, `pip install -r requirements.txt` will still attempt to build / install them.

**Impact:**
- On Windows, `psycopg2-binary` often fails to install without a pre-built wheel.
- On ARM free-tier containers (e.g., Fly.io free), `psycopg2-binary` can fail to build from source, blocking the entire Docker build.
- Inflates image size by ~50 MB+ for packages that are never used.

**Fix:** Move them to an optional extra in `pyproject.toml`:
```toml
[project.optional-dependencies]
postgres = ["asyncpg>=0.29", "psycopg2-binary>=2.9", "alembic>=1.13"]
worker = ["celery>=5.3", "redis>=5.0", "flower>=2.0"]
```
Update `requirements.txt` to only the core set, and document `pip install -e ".[postgres,worker]"` for full stack.

---

### 4. SQLite-only async DB is broken by design
**Severity:** P0  
**File:** `src/db.py:11-35`  
**What:** When `USE_POSTGRES=false`:
```python
engine = None
AsyncSessionLocal = None
```
And `get_db_session()` raises:
```python
raise RuntimeError("PostgreSQL is not configured. Set USE_POSTGRES=true ...")
```

No async SQLite engine is created. While the *main* app uses raw `sqlite3` modules (`storage.py`, `keys.py`, `teams.py`, etc.), any code path that relies on `AsyncSessionLocal` (jobs, tasks, health `/ready`) will fail at runtime.

**Impact:**
- `/v1/jobs` submit works for the SQLite path because `jobs.submit()` uses raw sqlite3, but the `jobs.py` router also imports `redis_client` (P0 #1) and `jobs.py` service calls Celery unconditionally (P0 #2).
- The `/v1/ready` health check will always report `postgres: false` because it tries to ping `db.engine` which is `None`.

**Fix:** Create an `aiosqlite` + SQLAlchemy async engine when `USE_POSTGRES=false`:
```python
if config.USE_POSTGRES:
    engine = create_async_engine(config.ASYNC_DATABASE_URL, ...)
else:
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(f"sqlite+aiosqlite:///{config.DB_PATH}")
    AsyncSessionLocal = async_sessionmaker(engine, ...)
```

---

## P1 — FEATURE BROKEN OR DEPLOYMENT FAILS

### 5. Health-check path `/health` returns 307 on Render, not 200
**Severity:** P1  
**File:** `api.py:132-146`, `render.yaml:44`, `src/routers/v1/health.py:12-15`  
**What:**
- The actual health endpoint lives at `/v1/health` (inside the `health_router`).
- `render.yaml` configures `healthCheckPath: /health` (root level).
- The `_legacy_redirect_middleware` in `api.py` catches `/health` and issues a `307` redirect to `/v1/health`.
- Render’s (and many other platforms’) health-check probes do **not** follow 307 redirects by default. They expect `200 OK`.
- Result: Render marks the service as **unhealthy** and refuses to route traffic, or keeps restarting the container.

**Fix:** Add a top-level `/health` endpoint directly on `app` in `api.py`, **and** add `/health` to `_EXCLUDE_REDIRECT` so it is not caught by the legacy middleware:
```python
# api.py
_EXCLUDE_REDIRECT = {
    "/", "/health", "/ready", "/metrics",
    "/docs", "/openapi.json", "/openapi-static.json",
    "/redoc", "/redoc.html", "/favicon.ico",
}

@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}
```

---

### 6. `MaxBodySizeMiddleware` breaks `UploadFile` endpoints by consuming the request stream
**Severity:** P1  
**File:** `src/middleware.py:83-94`  
**What:** `MaxBodySizeMiddleware` does `await request.body()` for every POST/PUT/PATCH. In ASGI/Starlette, `request.body()` consumes the entire stream and caches it in `request._body`. For `multipart/form-data` (file uploads), `request.form()` (which FastAPI’s `UploadFile` relies on) needs to parse the raw stream. Once the stream is consumed by `body()`, `form()` sees an empty stream and returns no files.

**Impact:**
- `POST /v1/upload/compute` with an SDF/CSV file will silently fail or return `400` ("No valid molecules parsed") because the file body is empty by the time the endpoint runs.
- This is a classic ASGI middleware foot-gun.

**Fix:** Do not read `request.body()` in middleware. Use `Content-Length` header instead:
```python
class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method in ("POST", "PUT", "PATCH"):
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_size:
                raise HTTPException(413, "Request body too large")
        return await call_next(request)
```
If you truly need to guard chunked-encoded requests, implement a streaming wrapper that counts bytes instead of buffering.

---

### 7. Only 2 out of 5 ONNX models are present — `/predict/ml` silently returns degraded heuristic results
**Severity:** P1  
**File:** `src/ml/models/`, `src/ml/predictor.py:34-40`  
**What:** The `ONNX_MODEL_MAP` declares 5 models:
- `aqueous_logs` → `logs_regressor.onnx` ✅ present
- `bbb_probability` → `bbb_classifier.onnx` ❌ missing
- `herg_risk` → `herg_regressor.onnx` ✅ present
- `gi_absorption` → `gi_classifier.onnx` ❌ missing
- `sa_score_lite` → `sa_regressor.onnx` ❌ missing

`predictor.py` falls back to heuristics when a model is missing, but the response schema still says `source: "onnx"` and `confidence: 0.85` (or `0.45` for heuristic). The caller has no way to know that 3/5 predictions are actually rule-based guesses unless they inspect the `warning` field, which is not documented in the OpenAPI schema.

**Impact:**
- Users paying for "ML predictions" are getting heuristics without clear warning.
- Model card accuracy claims (`expected_r2: 0.892` for logS) are misleading when the model is missing.

**Fix:**
1. Either ship all 5 ONNX models, or
2. Change the `/predict/ml` endpoint to explicitly return `source: "heuristic"` and `model_version: "heuristic-v1"` for missing models, and expose a `models_available` field in the response so the client knows which properties are actually ML-based.

---

### 8. PostgreSQL tables are never auto-created on first run
**Severity:** P1  
**File:** `src/db.py:39-43`, `api.py:38-43`  
**What:** `init_db()` exists in `src/db.py` but is **never called**. The `lifespan` in `api.py` only calls `close_db()`. For SQLite, every module (`storage.py`, `keys.py`, etc.) runs its own `CREATE TABLE IF NOT EXISTS` inside `connect()`. For PostgreSQL, nothing creates the tables. If you deploy with `USE_POSTGRES=true` and run the app, you get `sqlalchemy.exc.InvalidRequestError` or `asyncpg.UndefinedTableError` on the first request that touches the DB.

**Fix:** Call `init_db()` in `lifespan` when `USE_POSTGRES=true`:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    if config.USE_POSTGRES:
        from src.db import init_db
        await init_db()
    yield
    from src.db import close_db
    await close_db()
```

---

### 9. `email-validator` can crash startup if missing, yet is not a hard declared dependency in `pyproject.toml`
**Severity:** P1  
**File:** `src/routers/v1/billing.py:2`, `requirements.txt:39`  
**What:** `billing.py` uses `EmailStr` from Pydantic. Pydantic v2 resolves `EmailStr` at model-definition time, which triggers `email-validator`. It is listed in `requirements.txt` but if a user installs via `pip install -e .` using `pyproject.toml` alone, it may be missing because `pyproject.toml` in the repo does not list it:
```toml
# pyproject.toml (current)
dependencies = [
    "rdkit>=2024.3.1",
    ...
]
```
The `pyproject.toml` only has a stub list (about 7 packages) and is missing `email-validator`, `bcrypt`, `python-multipart`, etc.

**Fix:** Sync `pyproject.toml` with `requirements.txt`, or delete `pyproject.toml` and make `requirements.txt` the single source of truth. Add `email-validator>=2.0` explicitly.

---

### 10. Job streaming endpoint (`/jobs/{job_id}/stream`) has no Redis fallback
**Severity:** P1  
**File:** `src/routers/v1/jobs.py:102-143`  
**What:** The SSE endpoint does:
```python
r = redis_client.get_redis()
channel = f"job:{job_id}:progress"
pubsub = r.pubsub()
await pubsub.subscribe(channel)
```
If Redis is installed but the server is down (or the connection times out), this endpoint will crash with a `ConnectionError` and no fallback. The `redis_client` module has `try/except` wrappers for `publish_progress_sync` and `store_progress_sync`, but the **consumer** (`job_stream`) does not.

**Fix:** Wrap the Redis connection in `try/except` and fall back to a polling loop against the SQLite `jobs` table (or return a simple SSE stream that sends "waiting" until the job status changes via polling).

---

## P2 — DEGRADED / RISKY / BRITTLE

### 11. Memory footprint is dangerously close to 512 MB free-tier limits
**Severity:** P2  
**What:**
- **RDKit** shared libraries on Windows/Linux: ~150–300 MB RSS (C++ cheminformatics engine).
- **Python + NumPy + Pandas + PyArrow**: ~80–120 MB.
- **FastAPI + Uvicorn + all routers imported**: ~40–60 MB.
- **ONNX models**: ~1 MB (loaded on first `get_predictor()` call).
- **Total estimated RSS at steady state:** 300–500 MB.

**Impact:** On Render free (512 MB) or Fly.io free (256 MB), the app may be OOM-killed during peak load or when multiple RDKit molecules are processed concurrently.

**Fix:**
- Profile with `memory_profiler` and `tracemalloc` during startup.
- Consider `--limit-max-requests` on Uvicorn to recycle workers before memory bloats.
- On 256 MB tiers, you may need to drop `pandas`/`pyarrow` exports (parquet) and replace with `csv` only.

---

### 12. Dead-weight dependencies bloat the image and build time
**Severity:** P2  
**File:** `requirements.txt`  
**What:** The following packages are required in `requirements.txt` but are **never imported** by the API server at runtime:
- `scikit-learn>=1.4` — only used in `scripts/train_models.py` and `scripts/export_onnx.py`.
- `flower>=2.0` — only a CLI tool (`celery -A src.celery_app flower`).
- `apscheduler>=3.10` — not imported anywhere in `src/`.
- `kaggle>=1.6` — only used in `src/kaggle_publish.py` (standalone script, not imported by API).

**Fix:** Split into `requirements.txt` (core) and `requirements-optional.txt` or use `pyproject.toml` extras:
```toml
[project.optional-dependencies]
ml = ["scikit-learn>=1.4", "onnxruntime>=1.17"]
worker = ["celery>=5.3", "redis>=5.0", "flower>=2.0"]
publish = ["kaggle>=1.6", "huggingface_hub>=0.24"]
```

---

### 13. All 40+ routers are imported unconditionally — slow cold start
**Severity:** P2  
**File:** `src/routers/v1/__init__.py`  
**What:** Every router (DTI, pharmacophore, generation, NLP, billing, admin, etc.) is imported at startup. This means:
- Slow import time (~2–5 seconds on a low-end VPS).
- High memory baseline even if the user only calls `/compute`.
- If any single router has a broken dependency, the whole app crashes.

**Fix:** Use lazy router loading. In `src/routers/v1/__init__.py`, import routers only when first requested, or split the app into blueprints and mount them conditionally based on env vars.

---

### 14. Root endpoint `/` always tries SQLite even in PostgreSQL mode
**Severity:** P2  
**File:** `api.py:160-170`  
**What:** The root `/` endpoint does:
```python
conn = storage.connect(config.DB_PATH)
n = storage.row_count(conn)
```
`config.DB_PATH` is always `data/qmol.sqlite`, regardless of `USE_POSTGRES`. When `USE_POSTGRES=true`, the endpoint still opens SQLite and queries a potentially empty or stale local file. It has a `try/except` so it won’t crash, but the `public_rows` count is meaningless in Postgres mode.

**Fix:** Branch on `config.USE_POSTGRES`:
```python
if config.USE_POSTGRES:
    from src.db import engine
    from sqlalchemy import text
    async with engine.connect() as conn:
        n = (await conn.execute(text("SELECT COUNT(*) FROM molecules WHERE success=1"))).scalar()
else:
    conn = storage.connect(config.DB_PATH)
    n = storage.row_count(conn)
    conn.close()
```

---

### 15. No `X-Forwarded-Proto` / HTTPS trust behind reverse proxy
**Severity:** P2  
**File:** `api.py`, `src/middleware.py`  
**What:**
- `TrustedHostMiddleware` is added if `ALLOWED_HOSTS` is set, but it does not handle `X-Forwarded-Proto`.
- If the app sits behind an HTTPS reverse proxy (e.g., Nginx, Cloudflare, Render’s TLS terminator), the app generates HTTP URLs in OpenAPI docs and `request.url.scheme` returns `http`, which breaks OAuth callbacks and Stripe webhooks.
- `TRUSTED_PROXIES` is read for `X-Forwarded-For`, but there is no equivalent for `X-Forwarded-Proto`.

**Fix:** Add a tiny middleware that sets `request.scope["scheme"] = "https"` when `X-Forwarded-Proto: https` comes from a trusted proxy.

---

### 16. CORS `ALLOWED_ORIGINS` wildcard handling is technically correct but brittle
**Severity:** P2  
**File:** `api.py:60-72`  
**What:** The code does:
```python
_allowed_origins = [o.strip() for o in _allowed_origins_str.split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_allowed_origins, ...)
```
If `ALLOWED_ORIGINS=*`, it passes `allow_origins=["*"]`. FastAPI’s `CORSMiddleware` does **not** allow `credentials=True` with wildcard. The code does not set `allow_credentials=True`, so this is fine for now. But if a future refactor adds `allow_credentials=True`, the wildcard will be rejected by browsers.

**Fix:** Document that `ALLOWED_ORIGINS=*` disables credentials. If you need cookies/auth headers, require explicit origins.

---

### 17. `_legacy_redirect_middleware` can interfere with API clients and health probes
**Severity:** P2  
**File:** `api.py:140-146`  
**What:** Every non-`/v1/` path gets a `307` redirect to `/v1/`. This is fine for browser users, but API clients that expect `404` for unknown paths will instead get `307` and then (if they follow) `200`. This can mask typos in client code.

**Fix:** Make the redirect middleware opt-in via an env var (`ENABLE_LEGACY_REDIRECT=true`) or remove it entirely in v2.1. The API has been on `/v1/` for a while; clients should have migrated.

---

### 18. `Dockerfile` duplicates already-installed packages
**Severity:** P2  
**File:** `Dockerfile:23-24`  
**What:**
```dockerfile
RUN pip install -r requirements.txt \
 && pip install "fastapi>=0.110" "uvicorn>=0.27" "email-validator>=2" "python-multipart>=0.0.20"
```
These four packages are already listed in `requirements.txt`. The extra install adds build time and layer size with no benefit.

**Fix:** Remove the second `pip install` line.

---

### 19. `requests` is imported lazily in webhook modules but listed as required
**Severity:** P2 (non-blocking, but inconsistent)  
**File:** `src/webhooks/service.py:19-22`, `src/webhooks_out.py:16-19`  
**What:** Both webhook modules wrap `import requests` in `try/except`. If `requests` is missing, webhooks silently fail (`return False`). This is good graceful degradation. However, `requests>=2.31` is listed as a required dependency. It should be optional.

**Fix:** Move `requests` to `requirements-optional.txt` or an `[webhooks]` extra.

---

### 20. `compute.py` `try/except` for `pyscf` and `pyqpanda` is good, but `HAS_PYSCF` / `HAS_PYQPANDA` are checked at import time
**Severity:** P2  
**File:** `src/compute.py:34-44`  
**What:** The imports are wrapped in `try/except` at module level, which is correct. However, the `HAS_PYSCF = True/False` flag is checked later. If `pyscf` is installed but fails to import (e.g., missing BLAS), the exception is swallowed silently. The app starts, but quantum chemistry is silently disabled. This is fine for deployment, but could confuse a developer who thinks PySCF is active.

**Fix:** Log a warning at startup when an optional dependency is present but fails to import:
```python
except Exception as e:
    HAS_PYSCF = False
    log.warning("pyscf import failed: %s", e)
```

---

## Summary Table

| # | Issue | Severity | Won't Start? | Free-Tier Blocker? |
|---|-------|----------|--------------|-------------------|
| 1 | Redis imported unconditionally | P0 | ✅ Yes | ✅ Yes |
| 2 | Celery imported unconditionally | P0 | ✅ Yes | ✅ Yes |
| 3 | `asyncpg`/`psycopg2` required for SQLite | P0 | ✅ Build | ✅ Yes |
| 4 | SQLite async engine missing | P0 | ⚠️ Runtime | ⚠️ Partial |
| 5 | `/health` returns 307, not 200 | P1 | ❌ No | ✅ Yes (Render) |
| 6 | `MaxBodySizeMiddleware` breaks uploads | P1 | ❌ No | ❌ No |
| 7 | 3 of 5 ONNX models missing | P1 | ❌ No | ❌ No |
| 8 | Postgres tables never auto-created | P1 | ❌ No | ❌ No |
| 9 | `email-validator` not in `pyproject.toml` | P1 | ✅ Yes | ⚠️ Partial |
| 10 | Job SSE stream has no Redis fallback | P1 | ❌ No | ❌ No |
| 11 | Memory ~300–500 MB, near 512 MB limit | P2 | ❌ No | ✅ Yes (risk) |
| 12 | Dead-weight deps (`sklearn`, `flower`, `apscheduler`) | P2 | ❌ No | ❌ No |
| 13 | All routers imported unconditionally | P2 | ❌ No | ✅ Yes (slow cold start) |
| 14 | Root `/` always hits SQLite | P2 | ❌ No | ❌ No |
| 15 | No `X-Forwarded-Proto` trust | P2 | ❌ No | ❌ No |
| 16 | CORS wildcard OK but brittle | P2 | ❌ No | ❌ No |
| 17 | Legacy redirect middleware | P2 | ❌ No | ❌ No |
| 18 | Dockerfile duplicates pip installs | P2 | ❌ No | ❌ No |
| 19 | `requests` should be optional | P2 | ❌ No | ❌ No |
| 20 | PySCF import failures swallowed silently | P2 | ❌ No | ❌ No |

---

## Recommended Fix Order (MVP for Free-Tier Deploy)

1. **Split `requirements.txt`** into core vs optional (Redis, Celery, Postgres). Update `pyproject.toml` to match.
2. **Make Redis and Celery lazy imports** in `src/redis_client.py`, `src/jobs.py`, and `src/celery_app.py`.
3. **Add top-level `/health` and `/ready`** directly in `api.py` and exclude them from redirect middleware.
4. **Fix `MaxBodySizeMiddleware`** to use `Content-Length` instead of `await request.body()`.
5. **Add `aiosqlite` async engine** in `src/db.py` when `USE_POSTGRES=false`.
6. **Call `init_db()` in `lifespan`** when `USE_POSTGRES=true`.
7. **Profile memory** on target hardware and remove `pandas`/`pyarrow` if under 512 MB.
8. **Either ship missing ONNX models or fix `/predict/ml`** to honestly report heuristic fallback.

---

*Report generated by code analysis of `D:\Qmol-3`. All findings are reproducible by reading the listed files.*
