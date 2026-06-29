from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field, ConfigDict
from typing import Annotated
from pathlib import Path

from src import (
    keys as keysdb, usage_stats, audit, exporters, invoices, referrals,
    scopes, rotate as rotatelib, result_cache, compute, parquet_out, sdf_out,
)
from src.dependencies import (
    _client_ip, _rl, require_admin, check_quota, record_usage
)
import config

router = APIRouter(tags=["misc"])


class SdfDownloadIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"smiles": ["CCO"], "with_coords": False}})
    smiles: list[str] = Field(..., min_length=1, max_length=10000)
    with_coords: bool = False


class ParquetIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"smiles": ["CCO"]}})
    smiles: list[str] = Field(..., min_length=1, max_length=50000)


class ScopesIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"scopes": ["compute", "predict"]}})
    scopes: list[str] = Field(..., max_length=50)


def _run_compute(smiles_list: list[str]) -> list[dict]:
    out = []
    for i, smi in enumerate(smiles_list):
        d = result_cache.memoize(
            "compute", smi,
            lambda i=i, smi=smi: compute.compute_molecule(cid=-(i + 1), smiles=smi).to_dict(),
        )
        out.append(d)
    return out


@router.get("/")
def root():
    try:
        from src import storage
        conn = storage.connect(config.DB_PATH)
        n = storage.row_count(conn)
        conn.close()
    except Exception:
        n = 0
    return {"status": "ok", "public_rows": n, "docs": "/docs"}


@router.get("/status")
def status_page():
    from src import status_store
    return {
        "24h": status_store.summary(window_seconds=24 * 3600),
        "7d": status_store.summary(window_seconds=7 * 24 * 3600),
        "recent": status_store.recent(limit=30),
    }


@router.get("/badge/uptime")
def uptime_badge(days: int = 7):
    days = max(1, min(days, 90))
    s = usage_stats.global_slo(days=days)
    pct = s["slo"] * 100.0
    color = ("brightgreen" if pct >= 99.9 else
             "green" if pct >= 99.5 else
             "yellow" if pct >= 99.0 else "red")
    return {"schemaVersion": 1, "label": f"uptime {days}d",
            "message": f"{pct:.3f}%", "color": color, **s}


@router.get("/usage")
def usage(x_api_key: str | None = Header(default=None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key")
    info = keysdb.lookup(x_api_key)
    if not info:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {
        "tier": info.tier,
        "used_this_month": keysdb.month_usage(x_api_key),
        "monthly_quota": info.monthly_quota,
        "active": info.active,
    }


@router.get("/usage/history")
def usage_history(
    x_api_key: str | None = Header(default=None),
    days: int = 30,
):
    if not x_api_key or not keysdb.lookup(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    days = max(1, min(days, 365))
    return {
        "days": days,
        "daily": usage_stats.daily_counts(x_api_key, days=days),
        "by_endpoint": usage_stats.endpoint_breakdown(x_api_key, days=days),
    }


@router.get("/invoice")
def invoice_current(
    x_api_key: str | None = Header(default=None),
    period: str | None = None,
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    if not keysdb.lookup(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    try:
        inv = invoices.generate(x_api_key, period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {**inv.to_dict(), "markdown": inv.to_markdown()}


@router.get("/invoice.csv")
def invoice_csv(
    x_api_key: str | None = Header(default=None),
    period: str | None = None,
):
    if not x_api_key or not keysdb.lookup(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    try:
        inv = invoices.generate(x_api_key, period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    body = exporters.to_csv([l.to_dict() for l in inv.lines],
                            columns=["endpoint", "calls", "smiles"])
    return PlainTextResponse(body, media_type="text/csv")


@router.get("/audit")
def audit_recent(
    x_api_key: str | None = Header(default=None),
    limit: int = 100,
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    if not keysdb.lookup(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    limit = max(1, min(limit, 1000))
    return {"events": audit.recent(x_api_key, limit=limit)}


@router.get("/audit.csv")
def audit_csv(
    x_api_key: str | None = Header(default=None),
    limit: int = 1000,
):
    if not x_api_key or not keysdb.lookup(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    rows = audit.recent(x_api_key, limit=max(1, min(limit, 10_000)))
    body = exporters.to_csv(rows, columns=["ts", "method", "path", "status", "ms", "n_smiles"])
    return PlainTextResponse(body, media_type="text/csv")


@router.get("/referral")
def referral_get(x_api_key: str | None = Header(default=None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info:
        raise HTTPException(status_code=401, detail="Invalid API key")
    code = referrals.code_for(x_api_key)
    s = referrals.stats(x_api_key)
    return {
        "code": code,
        "share_url": f"/?ref={code}",
        "total_referrals": s.total_referrals,
        "free_signups": s.free_signups,
        "paid_purchases": s.paid_purchases,
        "earned_usd": round(s.earned_cents / 100, 2),
        "bonus_smiles": s.bonus_smiles,
    }


@router.get("/key/scopes")
def get_key_scopes(x_api_key: str | None = Header(default=None)):
    if not x_api_key or not keysdb.lookup(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    sc = scopes.get_scopes(x_api_key)
    return {"scopes": sc, "unrestricted": sc is None, "known": sorted(scopes.KNOWN_SCOPES)}


@router.put("/key/scopes")
def set_key_scopes(
    body: ScopesIn,
    x_api_key: str | None = Header(default=None),
):
    if not x_api_key or not keysdb.lookup(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    try:
        saved = scopes.set_scopes(x_api_key, body.scopes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"scopes": saved}


@router.delete("/key/scopes")
def clear_key_scopes(x_api_key: str | None = Header(default=None)):
    if not x_api_key or not keysdb.lookup(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    scopes.clear_scopes(x_api_key)
    return {"scopes": None, "unrestricted": True}


@router.post("/key/rotate")
def key_rotate(x_api_key: str | None = Header(default=None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    _rl(f"keyrot:{x_api_key}", limit=3, window=3600.0)
    try:
        res = rotatelib.rotate(x_api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"old_key_suffix": res.old_key[-6:], "new_key": res.new_key,
            "email": res.email, "tier": res.tier}


@router.post("/auth/rotate")
def auth_rotate(x_api_key: str | None = Header(default=None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    _rl(f"rotate:{x_api_key}", limit=5, window=3600.0)
    try:
        res = rotatelib.rotate(x_api_key)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {
        "old_key_last12": res.old_key[-12:],
        "new_key": res.new_key,
        "email": res.email,
        "tier": res.tier,
    }


@router.get("/account/export")
def account_export(x_api_key: str | None = Header(default=None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {
        "account": {"email": info.email, "tier": info.tier,
                    "monthly_quota": info.monthly_quota, "active": info.active},
        "used_this_month": keysdb.month_usage(x_api_key),
        "usage_by_day": usage_stats.daily_counts(x_api_key, days=365),
        "usage_by_endpoint": usage_stats.endpoint_breakdown(x_api_key, days=365),
        "recent_requests": audit.recent(x_api_key, limit=1000),
    }


@router.delete("/account")
def account_delete(x_api_key: str | None = Header(default=None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    if not keysdb.lookup(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    try:
        result = keysdb.delete_account(x_api_key)
    except ValueError:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"deleted": True, **result}


@router.post("/download/sdf")
def download_sdf(
    body: SdfDownloadIn,
    x_api_key: str | None = Header(default=None),
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    _rl(f"sdf:{x_api_key}", limit=10, window=60.0)
    sdf = sdf_out.smiles_to_sdf(body.smiles, with_coords=body.with_coords)
    keysdb.record(x_api_key, "/download/sdf", len(body.smiles))
    return PlainTextResponse(
        sdf, media_type="chemical/x-mdl-sdfile",
        headers={"Content-Disposition": 'attachment; filename="qmol.sdf"'},
    )


@router.post("/export/parquet")
def export_parquet(
    body: ParquetIn,
    x_api_key: str | None = Header(default=None),
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    _rl(f"parq:{x_api_key}", limit=10, window=60.0)
    n = len(body.smiles)
    used, quota = check_quota(x_api_key, n)
    rows = _run_compute(body.smiles)
    blob = parquet_out.to_parquet_bytes(rows)
    keysdb.record(x_api_key, "/export/parquet", n)
    return Response(
        content=blob, media_type="application/octet-stream",
        headers={"Content-Disposition": 'attachment; filename="qmol.parquet"'},
    )


@router.get("/openapi-static.json", include_in_schema=False)
def openapi_static():
    p = Path(__file__).resolve().parents[3] / "landing" / "openapi.json"
    if p.exists():
        return FileResponse(p, media_type="application/json")
    raise HTTPException(status_code=404, detail="not found")


@router.get("/app", include_in_schema=False)
def landing_app():
    p = Path(__file__).resolve().parents[3] / "landing" / "index.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    raise HTTPException(status_code=404, detail="not found")


@router.get("/reference", include_in_schema=False)
def reference_page():
    p = Path(__file__).resolve().parents[3] / "landing" / "docs.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    raise HTTPException(status_code=404, detail="not found")


@router.get("/dashboard", include_in_schema=False)
def dashboard_page():
    p = Path(__file__).resolve().parents[3] / "landing" / "dashboard.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    raise HTTPException(status_code=404, detail="not found")


@router.get("/privacy", include_in_schema=False)
def privacy_page():
    p = Path(__file__).resolve().parents[3] / "landing" / "privacy.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    raise HTTPException(status_code=404, detail="not found")


@router.get("/terms", include_in_schema=False)
def terms_page():
    p = Path(__file__).resolve().parents[3] / "landing" / "terms.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    raise HTTPException(status_code=404, detail="not found")
