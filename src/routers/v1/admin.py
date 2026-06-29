from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict

from src import metrics, keys as keysdb, result_cache, audit
from src.dependencies import require_admin, _rl, _client_ip

router = APIRouter(tags=["admin"])


@router.get("/admin/stats")
def admin_stats(
    request: Request,
    x_admin_token: str | None = Header(default=None),
):
    ip = _client_ip(request)
    _rl(f"admin:{ip}", limit=5, window=60.0)
    require_admin(x_admin_token)
    try:
        from src import storage
        import config
        conn = storage.connect(config.DB_PATH)
        n = storage.row_count(conn)
        conn.close()
    except Exception:
        n = 0
    return metrics.metrics_today(n)


@router.get("/admin/top-users")
def admin_top_users(
    request: Request,
    x_admin_token: str | None = Header(default=None),
    limit: int = 20,
):
    ip = _client_ip(request)
    _rl(f"admin:{ip}", limit=5, window=60.0)
    require_admin(x_admin_token)
    c = keysdb._connect()
    rows = c.execute(
        "SELECT u.key, k.email, k.tier, SUM(u.smiles_count) AS n "
        "FROM usage u JOIN api_keys k ON k.key=u.key "
        "WHERE u.ts >= datetime('now','start of month') "
        "GROUP BY u.key ORDER BY n DESC LIMIT ?", (limit,),
    ).fetchall()
    c.close()
    return {"users": [
        {"email": r[1], "tier": r[2], "smiles_count": int(r[3] or 0)}
        for r in rows
    ]}


@router.get("/admin/history")
def admin_history(
    request: Request,
    x_admin_token: str | None = Header(default=None),
    days: int = 30,
):
    ip = _client_ip(request)
    _rl(f"admin:{ip}", limit=5, window=60.0)
    require_admin(x_admin_token)
    return {"history": metrics.history(limit=days)}


@router.get("/admin/cache")
def admin_cache_stats(
    request: Request,
    x_admin_token: str | None = Header(default=None),
):
    ip = _client_ip(request)
    _rl(f"admin:{ip}", limit=5, window=60.0)
    require_admin(x_admin_token)
    return result_cache.COMPUTE_CACHE.stats()
