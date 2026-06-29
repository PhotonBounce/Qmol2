from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict

from src import metrics, keys as keysdb, result_cache, audit
from src.dependencies import require_admin

router = APIRouter(tags=["admin"])


@router.get("/admin/stats")
def admin_stats(x_admin_token: str | None = Header(default=None)):
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
    x_admin_token: str | None = Header(default=None),
    limit: int = 20,
):
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
    x_admin_token: str | None = Header(default=None),
    days: int = 30,
):
    require_admin(x_admin_token)
    return {"history": metrics.history(limit=days)}


@router.get("/admin/cache")
def admin_cache_stats(x_admin_token: str | None = Header(default=None)):
    require_admin(x_admin_token)
    return result_cache.COMPUTE_CACHE.stats()
