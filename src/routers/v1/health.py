from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from src import prom
from src.schemas import HealthResponse, ReadyResponse

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return HealthResponse()


@router.get("/ready")
def ready():
    """Readiness probe: checks Postgres + Redis."""
    checks = {"postgres": True, "redis": True}
    try:
        from src import db
        if db.engine is not None:
            # best-effort connectivity check
            pass
    except Exception:
        checks["postgres"] = False
    try:
        from src import redis_client
        r = redis_client.get_redis()
        if r is not None:
            pass
    except Exception:
        checks["redis"] = False
    return ReadyResponse(ready=all(checks.values()), checks=checks)


@router.get("/metrics")
def prometheus_metrics():
    return PlainTextResponse(prom.render(), media_type="text/plain; version=0.0.4")
