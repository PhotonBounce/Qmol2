from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from typing import Annotated

from src import prom
from src.schemas import HealthResponse, ReadyResponse
from src.dependencies import require_api_key_or_env

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return HealthResponse()


@router.get("/ready")
async def ready():
    """Readiness probe: checks Postgres + Redis."""
    db_ok = False
    redis_ok = False
    try:
        from src import db
        if db.engine:
            from sqlalchemy import text
            async with db.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                db_ok = True
    except Exception:
        db_ok = False
    try:
        from src import redis_client
        r = redis_client.get_redis()
        await r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False
    return ReadyResponse(ready=db_ok and redis_ok, checks={"postgres": db_ok, "redis": redis_ok})


@router.get("/metrics")
def prometheus_metrics(
    _api_key: Annotated[str, Depends(require_api_key_or_env)]
):
    """Prometheus metrics — requires authentication."""
    return PlainTextResponse(prom.render(), media_type="text/plain; version=0.0.4")
