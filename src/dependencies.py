"""FastAPI dependency injection helpers for auth, quotas, rate-limiting.

Centralizes the repetitive _require_auth / _check_quota / _rate_limit logic
that was previously inlined across ~1,800 lines of api.py.
"""
from __future__ import annotations

import os
from typing import Annotated

from fastapi import Header, HTTPException, Request, Depends

from src import keys as keysdb, ratelimit, teams, scopes

ADMIN_TOKEN = os.getenv("QMOL_ADMIN_TOKEN", "")
# Legacy env-var keys (still supported for bootstrap / admin):
API_KEYS = {
    k.strip() for k in os.getenv("QMOL_API_KEYS", "").split(",") if k.strip()
}

FREE_LIMIT = 500
PAID_LIMIT = 50_000


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _require_admin(x_admin_token: str | None) -> None:
    if not ADMIN_TOKEN or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Admin token required")


def require_admin(
    x_admin_token: Annotated[str | None, Header(default=None)]
) -> None:
    _require_admin(x_admin_token)


def _rl(key: str, limit: int, window: float) -> None:
    try:
        ratelimit.check(key, limit, window)
    except ratelimit.RateLimited as e:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Retry after {e.retry_after:.1f}s",
            headers={"Retry-After": str(int(e.retry_after) + 1)},
        )


def rate_limit(key: str, limit: int, window: float) -> None:
    """Dependency-compatible rate limiter."""
    _rl(key, limit, window)


def require_api_key(
    x_api_key: Annotated[str | None, Header(default=None)]
) -> str:
    """Return the validated API key or raise 401."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    return x_api_key


def require_api_key_or_env(
    x_api_key: Annotated[str | None, Header(default=None)]
) -> str:
    """Return the API key (accepts env bootstrap keys too)."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    if x_api_key in API_KEYS:
        return x_api_key
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    return x_api_key


def check_quota(x_api_key: str, charge: int) -> tuple[int, int]:
    """Return (used, quota) after verifying the key won't exceed quota."""
    used, quota = teams.effective_quota(x_api_key)
    if quota <= 0:
        raise HTTPException(
            status_code=402,
            detail="Quota is disabled or misconfigured for this key",
        )
    if used + charge > quota:
        raise HTTPException(
            status_code=402,
            detail=f"Quota would be exceeded ({used}/{quota})",
        )
    return used, quota


def check_paid_limit(n: int) -> None:
    if n > PAID_LIMIT:
        raise HTTPException(status_code=413, detail=f"Max {PAID_LIMIT} SMILES per call")


def check_free_limit(n: int) -> None:
    if n > FREE_LIMIT:
        raise HTTPException(
            status_code=413,
            detail=f"Free tier limit {FREE_LIMIT}. Use /compute/premium with API key.",
        )


def record_usage(x_api_key: str, endpoint: str, smiles_count: int) -> None:
    keysdb.record(x_api_key, endpoint, smiles_count)


def check_scopes(request: Request, x_api_key: str | None) -> None:
    """FastAPI dependency to enforce per-key endpoint scopes."""
    path = request.url.path
    if x_api_key and path not in ("/", "/health", "/metrics", "/v1/health", "/v1/ready", "/v1/metrics") \
            and not path.startswith(("/admin", "/badge", "/key", "/account", "/v1/admin", "/v1/badge", "/v1/key", "/v1/account")):
        try:
            if not scopes.allowed(x_api_key, path):
                raise HTTPException(
                    status_code=403,
                    detail=f"API key not permitted for {path}",
                )
        except Exception:
            pass  # never break the request path on a scope-table error


# Internal aliases used by v1 routers
_require_auth = require_api_key_or_env
_check_quota = check_quota
