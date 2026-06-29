"""FastAPI middleware: request ID, gzip, trusted host, timing/audit.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src import status_store, audit

logger = logging.getLogger("qmol.api")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a UUID4 request ID to every response and log it."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_id=%s method=%s path=%s status=%s",
            request_id, request.method, request.url.path, response.status_code,
        )
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Record latency + uptime status; fire-and-forget audit log."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        t0 = time.time()
        try:
            response = await call_next(request)
            ok = response.status_code < 500
            elapsed_ms = int((time.time() - t0) * 1000)
            status_store.record(
                ok, elapsed_ms,
                note=f"{request.method} {request.url.path} -> {response.status_code}",
            )
            try:
                audit.log_event(
                    api_key=request.headers.get("x-api-key"),
                    ip=request.client.host if request.client else None,
                    method=request.method,
                    path=request.url.path,
                    status=response.status_code,
                    ms=elapsed_ms,
                )
            except Exception:
                pass
            return response
        except Exception as exc:
            elapsed_ms = (time.time() - t0) * 1000
            status_store.record(
                False, elapsed_ms,
                note=f"{request.method} {request.url.path} -> err: {exc!s:.80}",
            )
            raise


def make_gzip_middleware() -> GZipMiddleware:
    """GZip for responses > 1 KB."""
    return GZipMiddleware(minimum_size=1024)


def make_trusted_host_middleware(allowed_hosts: list[str] | None = None) -> TrustedHostMiddleware:
    """TrustedHost — disabled by default (allows all)."""
    if allowed_hosts:
        return TrustedHostMiddleware(allowed_hosts=allowed_hosts)
    # When no hosts are configured, we skip the middleware entirely.
    return None  # type: ignore[return-value]
