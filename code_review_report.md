# Q-Mol v2.0.0 Deep Code Review Report

**Reviewer:** Senior QA Engineer  
**Scope:** 8-stage upgrade (new code in `src/`, `api.py`, `config.py`)  
**Directory:** `D:\Qmol-3`  
**Date:** 2026-01-25

---

## Executive Summary

| Severity | Count | Status |
|----------|-------|--------|
| **Critical** | 7 | Must fix immediately |
| **Warning** | 8 | Should fix before production |
| **Minor** | 7 | Recommend fixing in next sprint |
| **Total** | **22** | |

---

## Critical Bugs (must fix immediately)

### 1. `ImportError: cannot import name 'result_cache'` — module name mismatch
**File:** `src/routers/v1/compute.py` line 8  
**Also in:** `src/routers/v1/admin.py:4`, `src/routers/v1/uploads.py:4`, `src/routers/v1/misc.py:9`

**Description:** Four router modules import `result_cache` from `src`, but the actual module is `src/cache.py`. Because `src/__init__.py` is empty, Python cannot resolve `result_cache` as a submodule. This causes `ImportError` on application startup, crashing the entire FastAPI app.

**Suggested fix:**
```python
# Replace:
from src import compute, storage, result_cache, ratelimit
# With:
from src import compute, storage, cache as result_cache, ratelimit
```
Apply the same fix in `admin.py`, `uploads.py`, and `misc.py`.

---

### 2. Redis sliding-window rate limiter adds blocked requests to the window
**File:** `src/redis_client.py` lines 50–64

**Description:** `rate_limit_check()` uses a Redis pipeline that executes `zremrangebyscore → zcard → zadd → expire` atomically. `zcard` returns the count **before** `zadd`. If `current_count >= max_requests`, the request is blocked (`return False`), but `zadd` has already executed in the pipeline, permanently adding the blocked request's timestamp to the window. This means blocked requests consume slots, making the window never recover from bursts. The rate limiter is effectively broken under load.

**Suggested fix:** Use a two-phase approach or Lua script:
```python
async def rate_limit_check(key: str, max_requests: int, window_seconds: int) -> bool:
    r = get_redis()
    now = time.time()
    window_start = now - window_seconds
    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zcard(key)
    _, current_count = await pipe.execute()
    if current_count >= max_requests:
        return False
    # Only add if allowed
    pipe = r.pipeline()
    pipe.zadd(key, {str(now): now})
    pipe.expire(key, window_seconds)
    await pipe.execute()
    return True
```

---

### 3. `cancel()` overwrites completed jobs as "failed"
**File:** `src/jobs.py` lines 262–293

**Description:** `cancel()` unconditionally sets `status='failed'` and `error='cancelled by user'` in the database, even if the job has already finished successfully. A client calling `DELETE /jobs/{job_id}` on a completed job will corrupt the result record, making it appear as a failed job. The Celery `revoke(terminate=True)` also raises if the task has already completed.

**Suggested fix:** Check the current status before updating:
```python
def cancel(job_id: str) -> bool:
    info = get(job_id)
    if info and info.status in ("done", "failed"):
        return False  # Already terminal
    try:
        from celery.result import AsyncResult
        result = AsyncResult(job_id, app=app)
        result.revoke(terminate=True)
    except Exception:
        pass
    # ... update DB only if not terminal
```

---

### 4. Health `/ready` endpoint does not actually check service connectivity
**File:** `src/routers/v1/health.py` lines 16–33

**Description:** The `ready()` function imports `db` and `redis_client` but only checks `if db.engine is not None:` (object existence) and `if r is not None:` (object existence). It never executes a `SELECT 1` or `PING` against PostgreSQL or Redis. A dead database connection or disconnected Redis will still return `{"ready": True}`, which defeats Kubernetes/Docker readiness probes.

**Suggested fix:**
```python
@router.get("/ready")
async def ready():
    checks = {"postgres": False, "redis": False}
    try:
        from sqlalchemy import text
        from src.db import engine
        if engine is not None:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["postgres"] = True
    except Exception:
        checks["postgres"] = False
    try:
        from src import redis_client
        r = redis_client.get_redis()
        await r.ping()
        checks["redis"] = True
    except Exception:
        checks["redis"] = False
    return ReadyResponse(ready=all(checks.values()), checks=checks)
```

---

### 5. Path traversal risk in `/jobs/{job_id}/result`
**File:** `src/routers/v1/jobs.py` lines 74–86

**Description:** `job_result()` returns `FileResponse(info.result_path, ...)` without validating that `result_path` is inside the expected `JOBS_DIR`. Although `result_path` is set by the Celery task, a compromised database or race condition could allow arbitrary file reads (e.g., `../../etc/passwd`).

**Suggested fix:**
```python
from pathlib import Path
JOBS_DIR = Path("data/jobs").resolve()

@router.get("/jobs/{job_id}/result")
def job_result(...):
    # ... existing auth checks ...
    if not info.result_path:
        raise HTTPException(status_code=404, detail="No result")
    resolved = Path(info.result_path).resolve()
    if not str(resolved).startswith(str(JOBS_DIR)):
        raise HTTPException(status_code=403, detail="Invalid result path")
    return FileResponse(resolved, ...)
```

---

### 6. `check_scopes` in `dependencies.py` is dead code with a path-matching bug
**File:** `src/dependencies.py` lines 113–125

**Description:** `check_scopes()` is defined but never imported or used by any router. If it were ever used, it would fail because `scopes.allowed()` (from `src/scopes.py`) expects paths like `"compute"`, but `request.url.path` is `/v1/compute`. The `allowed()` function does NOT strip `/v1/` (only `path_to_scope()` strips leading slashes, but not the `/v1/` prefix). The middleware in `api.py` correctly strips `/v1/` before calling `scopes.allowed()`, but `check_scopes` does not.

**Suggested fix:** Either remove the dead function, or fix it to strip `/v1/` before calling `scopes.allowed()`:
```python
path = request.url.path
if path.startswith("/v1/"):
    path = path[3:]
```

---

## Warnings (should fix before production)

### 7. Hardcoded database pool size
**File:** `src/db.py` line 13

**Description:** `pool_size=20` is hardcoded. Different deployment environments (local dev, CI, production) need different pool sizes. Production may need 20–50, but local dev should be much smaller.

**Suggested fix:**
```python
pool_size=int(os.getenv("DB_POOL_SIZE", "20"))
```

---

### 8. No shutdown hook calls `close_db()`
**File:** `src/db.py` lines 45–48

**Description:** `close_db()` is defined but never wired to a FastAPI lifespan event or `atexit` handler. On SIGTERM, asyncpg connections may leak.

**Suggested fix:** Add a lifespan handler in `api.py`:
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_db()

app = FastAPI(..., lifespan=lifespan)
```

---

### 9. Celery hard time limit may be too short for large batches
**File:** `src/celery_app.py` line 21

**Description:** `task_time_limit=3600` (1 hour) is hardcoded. The `JobSubmitIn` schema allows up to 200,000 SMILES. The `compute_batch_task` processes each SMILES individually and writes progress every 50 items. 200,000 molecules in 1 hour requires ~55 molecules/second, which is unrealistic for quantum descriptor computations. Large batches will be killed mid-flight.

**Suggested fix:** Either increase the limit for large batches, or cap the batch size in the submit endpoint to a reasonable limit (e.g., 50,000) that fits within the time limit.

---

### 10. `pubsub.aclose()` may not exist in `redis-py`
**File:** `src/routers/v1/jobs.py` line 121

**Description:** `await pubsub.aclose()` is used. In `redis-py` 5.x, the async pubsub object uses `close()` or `reset()`, not `aclose()`. This may raise `AttributeError` when the SSE stream ends, leaking the pubsub connection.

**Suggested fix:** Use `await pubsub.close()` or `await pubsub.reset()` depending on the `redis-py` version. Also consider wrapping in `try/except`.

---

### 11. Stripe global API key mutation on every checkout request
**File:** `src/routers/v1/billing.py` line 111

**Description:** `stripe.api_key = secret` mutates global module state on every request. While the GIL makes this somewhat safe, it is bad practice and can cause race conditions in async workers or multi-process deployments.

**Suggested fix:** Use `stripe.api_key = secret` once at module load, or use per-request `stripe.checkout.Session.create(api_key=secret, ...)` if the library supports it.

---

### 12. Anonymous rate limit sharing for "unknown" IPs
**File:** `src/routers/v1/compute.py` line 120–124

**Description:** `compute_free()` uses `_rl(f"free:{ip}", ...)`. If `request.client` is `None` and `x-forwarded-for` is absent, `_client_ip()` returns `"unknown"`. All anonymous clients behind such proxies share the same `"free:unknown"` rate limit key, meaning one abusive client can block all others.

**Suggested fix:** Return a 403 or use a more granular fallback key (e.g., `request.headers.get("user-agent", "anon")[:20]`).

---

### 13. `include=["src.tasks"]` depends on launch working directory
**File:** `src/celery_app.py` line 11

**Description:** Celery's `include` path is relative to the Python path. If the worker is started from a subdirectory, task discovery will fail with `ModuleNotFoundError`.

**Suggested fix:** Document that workers must be started from the project root, or use an absolute module path and ensure `PYTHONPATH` is set correctly.

---

## Minor Issues (recommend fixing next sprint)

### 14. `Job.error` has no default empty string
**File:** `src/models.py` line 174

**Description:** `error: Mapped[Optional[str]] = mapped_column(Text)` has no default. The SQLite schema has `error TEXT` with no default. While nullable is fine, having an explicit default `=""` would avoid `None` checks downstream.

**Suggested fix:**
```python
error: Mapped[Optional[str]] = mapped_column(Text, default="")
```

---

### 15. `datetime.utcnow()` is deprecated in Python 3.12+
**File:** `src/tasks.py` lines 232, 248, 249, 250, 251

**Description:** `datetime.utcnow()` is deprecated. Will raise `DeprecationWarning` in future Python versions.

**Suggested fix:** Use `datetime.now(timezone.utc)` instead.

---

### 16. `require_api_key` dependency is imported but never used in `descriptors.py`
**File:** `src/routers/v1/descriptors.py` line 6

**Description:** `require_api_key` is imported but the router manually validates the key inline. Dead import.

**Suggested fix:** Remove the unused import, or refactor to use `require_api_key` as a dependency.

---

### 17. SSE stream missing `Cache-Control` headers
**File:** `src/routers/v1/jobs.py` lines 89–123

**Description:** The `StreamingResponse` for SSE does not include `Cache-Control: no-cache` or `X-Accel-Buffering: no`, which can cause proxy buffering (e.g., Nginx) and break real-time progress delivery.

**Suggested fix:**
```python
return StreamingResponse(
    event_generator(),
    media_type="text/event-stream",
    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
)
```

---

### 18. `check_quota` does not handle negative quotas
**File:** `src/dependencies.py` lines 85–93

**Description:** If `quota` is negative (e.g., misconfigured database), `used + charge > quota` is always True, blocking all requests. A negative quota is a data integrity issue, but the function should raise a distinct error or clamp the value.

**Suggested fix:** Add a guard:
```python
if quota <= 0:
    raise HTTPException(status_code=402, detail="Quota is disabled or misconfigured")
```

---

### 19. `_scope_middleware` in `api.py` duplicates `check_scopes` logic
**File:** `api.py` lines 70–93

**Description:** The middleware in `api.py` duplicates the scope-checking logic that also exists (unused) in `dependencies.py`. This is a maintenance risk if the rules diverge.

**Suggested fix:** Refactor `api.py` to import and use `dependencies.check_scopes` (after fixing the `/v1/` stripping bug in it).

---

### 20. `JobSubmitIn` max_length (200,000) exceeds practical Celery limits
**File:** `src/routers/v1/jobs.py` line 20

**Description:** `max_length=200000` is allowed, but the Celery time limit is 1 hour. Most batch tasks will not finish 200k items in 1 hour. The endpoint should either enforce a lower limit or dynamically adjust the Celery time limit per task.

**Suggested fix:** Lower `max_length` to 50,000 or compute a dynamic timeout based on batch size.

---

### 21. `models.py` defines many unused PostgreSQL models
**File:** `src/models.py` lines 79–295

**Description:** `ApiKey`, `Usage`, `Team`, `TeamMember`, `AuditLog`, `Coupon`, `RefCode`, `Referral`, `Invoice` models are defined but never queried via SQLAlchemy. The application uses raw SQLite modules (`keys.py`, `teams.py`, `audit.py`, etc.) instead. These models are created by `init_db()` but are dead code. This increases maintenance surface and risks schema drift.

**Suggested fix:** Either migrate the legacy modules to use the SQLAlchemy models, or remove the unused models to avoid confusion.

---

## Security Assessment

| Check | Status | Notes |
|-------|--------|-------|
| Hardcoded secrets | ✅ Pass | All secrets loaded from env vars |
| SQL injection (raw SQL) | ✅ Pass | Dynamic SQL in `tasks.py` and `keys.py` uses parameterized queries; table/column names are hardcoded |
| API key in plaintext headers | ✅ Pass | Standard practice for API keys |
| Path traversal in uploads | ⚠️ Warning | `uploads.parse()` reads from memory; no file path risk |
| Path traversal in job results | ❌ **Critical** | `/jobs/{job_id}/result` serves `result_path` without validation (issue #5) |
| Admin token check | ✅ Pass | `require_admin` correctly rejects if `ADMIN_TOKEN` is empty |
| `eval()` / `exec()` calls | ✅ Pass | None found |

---

## Missing Imports / Circular Dependencies

- **No circular dependencies detected** in the reviewed files.
- **Missing import:** `result_cache` (critical, 4 router files affected) — see issue #1.
- **Unused imports:** `require_api_key` in `descriptors.py`; `check_scopes` in `dependencies.py` (dead code).

---

## Recommended Priority Order

1. **Fix `result_cache` import** (app won't start)
2. **Fix Redis rate limiter** (production degradation under load)
3. **Fix `cancel()` overwriting done jobs** (data corruption)
4. **Fix `/ready` health check** (false-positive readiness = outages)
5. **Fix job result path traversal** (security)
6. **Fix `check_scopes` path bug** (if ever enabled)
7. **Address Celery time limit / batch size mismatch** (task failures)
8. **Add shutdown hook for DB dispose** (connection leaks)
