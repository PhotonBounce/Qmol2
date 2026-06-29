"""Async batch job manager — Celery edition.

Replaces the legacy SQLite+threading worker with a proper Celery distributed
queue.  Jobs are stored in PostgreSQL (when USE_POSTGRES=true) or SQLite
(fallback), and processed by Celery workers.

Jobs are charged against the owner's monthly quota at submit time (caller does
this) but refunded on failure by the Celery task itself.
"""
from __future__ import annotations
import asyncio
import json
import sqlite3
import uuid
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import config
from src.celery_app import app
from src import redis_client

DEFAULT_DB = Path("data/jobs.sqlite")
JOBS_DIR = Path("data/jobs")

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    api_key TEXT NOT NULL,
    endpoint TEXT DEFAULT '/jobs',
    status TEXT NOT NULL,
    n_smiles INTEGER NOT NULL,
    n_processed INTEGER DEFAULT 0,
    result_path TEXT,
    error TEXT,
    charge INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT
);
"""

_LOCK = False  # threading.Lock() removed — Celery handles concurrency
_WORKER_STARTED = False

_TASK_MAP = {
    "/jobs": "src.tasks.compute_batch_task",
    "/predict": "src.tasks.predict_batch_task",
    "/screen": "src.tasks.screen_batch_task",
    "/similarity": "src.tasks.similarity_search_task",
    "/cluster": "src.tasks.cluster_task",
    "/conformers": "src.tasks.conformer_generation_task",
    "/fingerprints": "src.tasks.fingerprint_batch_task",
}


@dataclass
class JobInfo:
    id: str
    status: str
    n_smiles: int
    n_processed: int
    result_path: str | None
    error: str | None
    endpoint: str = "/jobs"
    charge: int = 0


def _connect(path: Path | str | None = None) -> sqlite3.Connection:
    """Open SQLite connection with schema and migration applied."""
    p = Path(path or DEFAULT_DB)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.executescript(_SQLITE_SCHEMA)
    try:
        conn.execute("ALTER TABLE jobs ADD COLUMN endpoint TEXT DEFAULT '/jobs'")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE jobs ADD COLUMN charge INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    return conn


def _run_async(coro):
    """Run an async coroutine from a sync function safely."""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _insert_job_async(job_id: str, api_key: str, endpoint: str, status: str,
                             n_smiles: int, charge: int) -> None:
    """Insert a new job record into PostgreSQL."""
    from sqlalchemy import insert
    from src.db import AsyncSessionLocal
    from src.models import Job
    async with AsyncSessionLocal() as session:
        stmt = insert(Job).values(
            id=job_id,
            api_key=api_key,
            endpoint=endpoint,
            status=status,
            n_smiles=n_smiles,
            charge=charge,
        )
        await session.execute(stmt)
        await session.commit()


def submit(api_key: str, smiles: list[str], endpoint: str = "/jobs",
           charge: int | None = None) -> str:
    """Queue a job. Returns job id. Caller must charge quota before calling.

    Input is written to data/jobs/<id>.input.json for audit / idempotency.
    """
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    job_id = f"job_{uuid.uuid4().hex[:16]}"
    in_path = JOBS_DIR / f"{job_id}.input.json"
    in_path.write_text(json.dumps({
        "endpoint": endpoint,
        "smiles": smiles,
        "api_key": api_key,
        "charge": charge,
    }))

    n = len(smiles)
    actual_charge = charge if charge is not None else n

    if config.USE_POSTGRES:
        _run_async(_insert_job_async(job_id, api_key, endpoint, "queued", n, actual_charge))
    else:
        conn = _connect()
        conn.execute(
            "INSERT INTO jobs (id, api_key, endpoint, status, n_smiles, charge) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (job_id, api_key, endpoint, "queued", n, actual_charge),
        )
        conn.commit()
        conn.close()

    # Enqueue the appropriate Celery task with deterministic task_id
    task_name = _TASK_MAP.get(endpoint, "src.tasks.compute_batch_task")
    app.send_task(
        task_name,
        args=[job_id, smiles, api_key],
        task_id=job_id,
    )
    return job_id


def _get_job_info_sqlite(job_id: str) -> JobInfo | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id, status, n_smiles, n_processed, result_path, error, endpoint, charge "
            "FROM jobs WHERE id=?",
            (job_id,),
        ).fetchone()
    except sqlite3.OperationalError:
        row = conn.execute(
            "SELECT id, status, n_smiles, n_processed, result_path, error "
            "FROM jobs WHERE id=?",
            (job_id,),
        ).fetchone()
        if row:
            row = (*row, "/jobs", 0)
    conn.close()
    if not row:
        return None
    return JobInfo(*row)


async def _get_job_info_async(job_id: str) -> JobInfo | None:
    from sqlalchemy import select
    from src.db import AsyncSessionLocal
    from src.models import Job
    async with AsyncSessionLocal() as session:
        stmt = select(Job).where(Job.id == job_id)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return JobInfo(
            id=row.id,
            status=row.status,
            n_smiles=row.n_smiles,
            n_processed=row.n_processed or 0,
            result_path=row.result_path,
            error=row.error,
            endpoint=row.endpoint or "/jobs",
            charge=row.charge or 0,
        )


def get(job_id: str) -> JobInfo | None:
    """Query job status from DB and cross-check with Celery result backend."""
    if config.USE_POSTGRES:
        info = _run_async(_get_job_info_async(job_id))
    else:
        info = _get_job_info_sqlite(job_id)

    if not info:
        return None

    # Cross-check with Celery result backend for more accurate status
    if info.status in ("queued", "running"):
        try:
            from celery.result import AsyncResult
            result = AsyncResult(job_id, app=app)
            celery_state = result.state
            if celery_state == "STARTED":
                if info.status == "queued":
                    info.status = "running"
            elif celery_state == "SUCCESS":
                if info.status != "done":
                    info.status = "done"
            elif celery_state in ("FAILURE", "REVOKED"):
                if info.status not in ("failed", "done"):
                    info.status = "failed"
        except Exception:
            pass

    return info


def owner(job_id: str) -> str | None:
    """Return the API key that owns this job."""
    if config.USE_POSTGRES:
        from sqlalchemy import select
        from src.db import AsyncSessionLocal
        from src.models import Job

        async def _fetch():
            async with AsyncSessionLocal() as session:
                stmt = select(Job.api_key).where(Job.id == job_id)
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()
                return row
        return _run_async(_fetch())
    else:
        conn = _connect()
        row = conn.execute("SELECT api_key FROM jobs WHERE id=?", (job_id,)).fetchone()
        conn.close()
        return row[0] if row else None


async def get_progress(job_id: str) -> dict[str, Any] | None:
    """Read the latest progress snapshot from Redis (for polling / SSE init)."""
    try:
        r = redis_client.get_redis()
        data = await r.get(f"job:{job_id}:progress:last")
        return json.loads(data) if data else None
    except Exception:
        return None


def cancel(job_id: str) -> bool:
    """Revoke a running Celery task and mark the job as cancelled."""
    try:
        from celery.result import AsyncResult
        result = AsyncResult(job_id, app=app)
        result.revoke(terminate=True)
    except Exception:
        pass

    # Update DB
    if config.USE_POSTGRES:
        from sqlalchemy import update
        from src.db import AsyncSessionLocal
        from src.models import Job

        async def _update():
            async with AsyncSessionLocal() as session:
                stmt = update(Job).where(Job.id == job_id).values(
                    status="failed", error="cancelled by user"
                )
                await session.execute(stmt)
                await session.commit()
        _run_async(_update())
    else:
        conn = _connect()
        conn.execute(
            "UPDATE jobs SET status='failed', error='cancelled by user' WHERE id=?",
            (job_id,),
        )
        conn.commit()
        conn.close()
    return True


def start_worker() -> None:
    """Idempotent background worker starter.

    DEPRECATED: Celery workers run externally now (docker-compose worker service).
    This function is a no-op for backwards compatibility.
    """
    global _WORKER_STARTED
    if not _WORKER_STARTED:
        _WORKER_STARTED = True
        warnings.warn(
            "start_worker() is deprecated. Use Celery workers instead: "
            "celery -A src.celery_app worker --loglevel=info",
            DeprecationWarning,
            stacklevel=2,
        )


def run_pending_sync() -> int:
    """Run all queued jobs synchronously. Used in tests.

    This calls the appropriate Celery task synchronously via task.apply().
    """
    n = 0
    while True:
        conn = _connect()
        row = conn.execute(
            "SELECT id FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1"
        ).fetchone()
        conn.close()
        if not row:
            return n
        job_id = row[0]

        info = get(job_id)
        if not info:
            return n

        in_path = JOBS_DIR / f"{job_id}.input.json"
        if not in_path.exists():
            return n
        in_data = json.loads(in_path.read_text())
        smiles = in_data.get("smiles", [])
        endpoint = in_data.get("endpoint", "/jobs")
        api_key = in_data.get("api_key", "")

        task_name = _TASK_MAP.get(endpoint, "src.tasks.compute_batch_task")
        task = app.tasks[task_name]

        # Build args based on task signature
        if endpoint == "/jobs":
            task.apply(args=[job_id, smiles, api_key])
        elif endpoint == "/predict":
            task.apply(args=[job_id, smiles, api_key])
        elif endpoint == "/screen":
            task.apply(args=[job_id, smiles, api_key])
        elif endpoint == "/similarity":
            # Similarity needs a single query SMILES and top_k
            query_smiles = smiles[0] if smiles else ""
            task.apply(args=[job_id, query_smiles, 20, api_key])
        elif endpoint == "/cluster":
            task.apply(args=[job_id, smiles, 0.4, api_key])
        elif endpoint == "/conformers":
            query_smiles = smiles[0] if smiles else ""
            task.apply(args=[job_id, query_smiles, 10, api_key])
        elif endpoint == "/fingerprints":
            task.apply(args=[job_id, smiles, "morgan", 2048, 2, api_key])
        else:
            task.apply(args=[job_id, smiles, api_key])
        n += 1
