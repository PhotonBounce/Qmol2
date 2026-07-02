from __future__ import annotations

import time
from typing import Any

from fastapi import Request
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# -----------------------------------------------------------------------------
# Prometheus Metrics
# -----------------------------------------------------------------------------

REQUEST_COUNT = Counter(
    "compute_swarm_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_DURATION = Histogram(
    "compute_swarm_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

JOBS_CREATED_TOTAL = Counter(
    "compute_swarm_jobs_created_total",
    "Total jobs created",
)

WORK_UNITS_COMPLETED_TOTAL = Counter(
    "compute_swarm_work_units_completed_total",
    "Total work units completed",
)

WORKERS_ONLINE = Gauge(
    "compute_swarm_workers_online",
    "Number of workers currently online",
)


# -----------------------------------------------------------------------------
# ASGI Middleware
# -----------------------------------------------------------------------------

class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        method = request.method
        endpoint = request.url.path
        status = str(response.status_code)

        REQUEST_COUNT.labels(
            method=method, endpoint=endpoint, status=status
        ).inc()
        REQUEST_DURATION.labels(
            method=method, endpoint=endpoint
        ).observe(duration)

        return response


# -----------------------------------------------------------------------------
# Metrics Response Helper
# -----------------------------------------------------------------------------

def generate_metrics() -> bytes:
    return generate_latest()
