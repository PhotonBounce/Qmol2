"""FastAPI server: Q-Mol molecular descriptor & cheminformatics API.

Run locally:
    uvicorn api:app --host 0.0.0.0 --port 8000

Deploy: render.com or fly.io.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from contextlib import asynccontextmanager

from src.middleware import (
    RequestIDMiddleware,
    TimingMiddleware,
    MaxBodySizeMiddleware,
    SecurityHeadersMiddleware,
)
from starlette.middleware.gzip import GZipMiddleware
from src.routers.v1 import v1_router
from src import scopes as _scopes_mod

ADMIN_TOKEN = os.getenv("QMOL_ADMIN_TOKEN", "")

# Legacy env-var keys (still supported for bootstrap / admin):
API_KEYS = {
    k.strip() for k in os.getenv("QMOL_API_KEYS", "").split(",") if k.strip()
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler: startup and shutdown events."""
    # Initialize database tables on startup (SQLite auto-creates, PostgreSQL needs this)
    try:
        from src.db import init_db
        await init_db()
    except Exception as exc:
        import logging
        logging.getLogger("qmol.api").warning("Database init failed: %s", exc)
    yield
    from src.db import close_db
    await close_db()


app = FastAPI(
    title="Q-Mol API",
    version="2.0.0",
    lifespan=lifespan,
    description=(
        "Molecular descriptor, similarity search, drug-likeness screen, "
        "and ADMET prediction API.\n\n"
        "Get a free key: `POST /v1/signup`. Upgrade: https://qmol.app/checkout.html\n\n"
        "Postman collection: [qmol-postman.json](/qmol-postman.json)"
    ),
    contact={"name": "Q-Mol support", "email": "hi@qmol.app"},
    license_info={"name": "MIT (free tier) / Commercial (paid tiers)"},
)

# Parse ALLOWED_ORIGINS from env (comma-separated). Empty = no CORS (safest default).
_allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "").strip()
if _allowed_origins_str:
    _allowed_origins = [o.strip() for o in _allowed_origins_str.split(",") if o.strip()]
else:
    _allowed_origins = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(TimingMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(MaxBodySizeMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Optional trusted-host middleware (disabled if ALLOWED_HOSTS is empty)
_allowed_hosts = os.getenv("ALLOWED_HOSTS", "").strip()
if _allowed_hosts:
    _hosts = [h.strip() for h in _allowed_hosts.split(",") if h.strip()]
    if _hosts:
        from starlette.middleware.trustedhost import TrustedHostMiddleware
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=_hosts)


app.include_router(v1_router)

# ------------------------------------------------------------------
# Scope middleware (keep same logic as legacy _scope_middleware)
# ------------------------------------------------------------------
import logging

_logger = logging.getLogger("qmol.scope")

@app.middleware("http")
async def _scope_middleware(request: Request, call_next):
    key = request.headers.get("x-api-key")
    path = request.url.path
    # Normalize: strip /v1 prefix for scope lookup
    if path.startswith("/v1/"):
        check_path = path[3:]
    else:
        check_path = path
    if key and check_path not in (
        "/", "/health", "/metrics", "/ready", "/status"
    ) and not check_path.startswith(
        ("/admin", "/badge", "/key", "/account")
    ):
        try:
            if not _scopes_mod.allowed(key, check_path):
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    {"detail": f"API key not permitted for {check_path}"},
                    status_code=403,
                )
        except Exception as exc:
            # FAIL-CLOSED: if the scope check errors, deny the request
            _logger.error("Scope check error for key=%s path=%s: %s", key[:12] if key else None, check_path, exc)
            from fastapi.responses import JSONResponse
            return JSONResponse(
                {"detail": "Scope check failed"},
                status_code=403,
            )
    return await call_next(request)


# ------------------------------------------------------------------
# Backward-compatible redirect middleware: non-v1 paths -> /v1/
# ------------------------------------------------------------------
_EXCLUDE_REDIRECT = {
    "/", "/docs", "/openapi.json", "/openapi-static.json",
    "/redoc", "/redoc.html", "/favicon.ico",
    "/health", "/metrics", "/ready",
}
_EXCLUDE_PREFIXES = (
    "/v1/", "/landing/", "/static/", "/docs/", "/openapi",
)

@app.middleware("http")
async def _legacy_redirect_middleware(request: Request, call_next):
    path = request.url.path
    if path in _EXCLUDE_REDIRECT or any(path.startswith(p) for p in _EXCLUDE_PREFIXES):
        return await call_next(request)
    # Redirect everything else to /v1 equivalent, preserving query string
    query = str(request.url.query)
    target = f"/v1{path}"
    if query:
        target = f"{target}?{query}"
    return RedirectResponse(url=target, status_code=307)


# OpenAPI static JSON (legacy path, not in router)
@app.get("/openapi-static.json", include_in_schema=False)
def openapi_static():
    from fastapi.responses import FileResponse
    p = Path(__file__).parent / "landing" / "openapi.json"
    if p.exists():
        return FileResponse(p, media_type="application/json")
    raise HTTPException(status_code=404, detail="not found")


# Keep root health directly on app (not inside v1 router)
@app.get("/", include_in_schema=False)
def root():
    from src import storage
    import config
    try:
        conn = storage.connect(config.DB_PATH)
        n = storage.row_count(conn)
        conn.close()
    except Exception:
        n = 0
    return {"status": "ok", "public_rows": n, "docs": "/docs"}


# Top-level health endpoint for hosting probes (Render, Fly.io, etc.)
@app.get("/health", include_in_schema=False)
def health():
    """Simple health check for hosting platform probes."""
    return {"status": "ok", "version": "2.0.0"}


# Readiness check (can include DB connectivity if needed)
@app.get("/ready", include_in_schema=False)
def ready():
    """Readiness probe."""
    return {"ready": True}


# Metrics stub (for Prometheus-style monitoring)
@app.get("/metrics", include_in_schema=False)
def metrics():
    """Basic metrics stub."""
    return {"requests_total": 0}


def make_api_key(email: str, secret: str) -> str:
    """Deterministic API key generator used by the Stripe webhook delivery path."""
    h = hashlib.sha256(f"{email}|{secret}".encode()).hexdigest()
    return f"qmol_{h[:32]}"
