from __future__ import annotations

import asyncio
import time
import redis.asyncio as redis
from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import func, text
from typing import Any

from app.api import admin, auth, billing, jobs, workers
from app.config import settings
from app.core.rate_limit import is_rate_limited
from app.core.storage import check_minio_health
from app.db.database import engine, get_db
from app.models import Base, Worker, WorkerStatus
from app.monitoring import (
    PrometheusMiddleware,
    WORKERS_ONLINE,
    generate_metrics,
)

app = FastAPI(
    title="ComputeSwarm API",
    description="Distributed scientific computing platform orchestrator",
    version="1.0.0",
)

# CORS — configurable via CORS_ORIGINS env var (comma-separated).
# In production set CORS_ORIGINS=https://app.yourdomain.com
# WARNING: Never use allow_origins=["*"] with allow_credentials=True in production.
_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False if "*" in _cors_origins else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(workers.router)
app.include_router(billing.router)
app.include_router(admin.router)

# Prometheus request metrics
app.add_middleware(PrometheusMiddleware)

# Gzip compression for responses > 1 KB
app.add_middleware(GZipMiddleware, minimum_size=1024)


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    # Only add HSTS in production (HTTPS)
    if settings.app_env == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration = time.monotonic() - start
    user_id = None
    # Try to extract user ID from auth context if available
    try:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # We avoid decoding the full JWT here to keep it lightweight
            user_id = "authenticated"
    except Exception:
        pass
    # Log to stdout (structured logging can be added in V2)
    print(
        f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] "
        f"{request.method} {request.url.path} "
        f"{response.status_code} "
        f"{duration:.3f}s "
        f"user={user_id or 'anonymous'}"
    )
    return response


# ---------------------------------------------------------------------------
# Global rate limiter middleware (public endpoints: 100 req/min per IP)
# ---------------------------------------------------------------------------
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Skip health/metrics from global rate limit
    if request.url.path in ("/health", "/metrics"):
        return await call_next(request)

    client_ip = request.headers.get("X-Forwarded-For", request.client.host or "unknown")
    # Use the first IP in X-Forwarded-For if present
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()

    if is_rate_limited(f"ip:{client_ip}", limit=100, window_seconds=60):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded. Please slow down."},
        )
    return await call_next(request)


_redis_pool: redis.Redis | None = None


async def _get_redis() -> redis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_pool


@app.on_event("startup")
async def on_startup() -> None:
    # Test DB connection by creating tables (for dev; Alembic for prod)
    async with engine.begin() as conn:
        # In production, use Alembic migrations instead of create_all
        await conn.run_sync(Base.metadata.create_all)

    # Ping Redis
    r = await _get_redis()
    await r.ping()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.close()
    await engine.dispose()


@app.get("/health", response_class=JSONResponse)
async def health_check() -> dict[str, Any]:
    services: dict[str, bool] = {"db": False, "redis": False, "minio": False}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["db"] = True
    except Exception:
        pass

    try:
        r = await _get_redis()
        await r.ping()
        services["redis"] = True
    except Exception:
        pass

    try:
        await asyncio.to_thread(check_minio_health)
        services["minio"] = True
    except Exception:
        pass

    if all(services.values()):
        return {"status": "ok", "services": services}
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "unhealthy", "services": services},
    )


@app.get("/metrics")
async def metrics(db=Depends(get_db)) -> Response:
    """Prometheus metrics endpoint."""
    # Update workers_online gauge from DB
    count_stmt = select(func.count(Worker.id)).where(Worker.status == WorkerStatus.online)
    count_result = await db.execute(count_stmt)
    count = count_result.scalar_one()
    WORKERS_ONLINE.set(count)

    return Response(content=generate_metrics(), media_type="text/plain")
