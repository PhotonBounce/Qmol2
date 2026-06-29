"""Celery task definitions for all batch operations.

Each task:
- Updates job status in PostgreSQL (USE_POSTGRES=true) or SQLite (fallback)
- Reports progress via Redis pub/sub for SSE streaming
- Handles retries with exponential backoff (max 3 retries)
- Stores large results as files in data/jobs/
- Is idempotent: safe to retry
"""
from __future__ import annotations
import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import config
from src.celery_app import app
from src import redis_client
from src import compute, predict, screen, similarity, clustering, conformers, fingerprints
from src import keys as keysdb
from src import webhooks_out

JOBS_DIR = Path("data/jobs")
DEFAULT_DB = Path("data/jobs.sqlite")

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


def _sqlite_conn() -> sqlite3.Connection:
    """Open SQLite connection with schema and migration applied."""
    DEFAULT_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DEFAULT_DB))
    conn.executescript(_SQLITE_SCHEMA)
    # Lightweight migration: add new columns if they don't exist
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
    """Run an async coroutine from a sync Celery task safely."""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _update_job_async(job_id: str, **kwargs) -> None:
    """Update a job record in PostgreSQL via SQLAlchemy async."""
    from sqlalchemy import update
    from src.db import AsyncSessionLocal
    from src.models import Job
    async with AsyncSessionLocal() as session:
        stmt = update(Job).where(Job.id == job_id).values(**kwargs)
        await session.execute(stmt)
        await session.commit()


def _update_job_sync(job_id: str, **kwargs) -> None:
    """Update a job record in SQLite."""
    conn = _sqlite_conn()
    fields = []
    values = []
    for k, v in kwargs.items():
        fields.append(f"{k} = ?")
        values.append(v)
    sql = f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?"
    values.append(job_id)
    conn.execute(sql, values)
    conn.commit()
    conn.close()


def _update_job_db(job_id: str, **kwargs) -> None:
    """Dispatch to PostgreSQL or SQLite update helper."""
    if config.USE_POSTGRES:
        _run_async(_update_job_async(job_id, **kwargs))
    else:
        _update_job_sync(job_id, **kwargs)


def _get_job_info(job_id: str) -> dict[str, Any] | None:
    """Fetch a job record as a dict."""
    if config.USE_POSTGRES:
        from sqlalchemy import select
        from src.db import AsyncSessionLocal
        from src.models import Job

        async def _fetch():
            async with AsyncSessionLocal() as session:
                stmt = select(Job).where(Job.id == job_id)
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()
                if row is None:
                    return None
                return {
                    "id": row.id,
                    "api_key": row.api_key,
                    "endpoint": row.endpoint,
                    "status": row.status,
                    "n_smiles": row.n_smiles,
                    "n_processed": row.n_processed,
                    "result_path": row.result_path,
                    "error": row.error,
                    "charge": row.charge or 0,
                }
        return _run_async(_fetch())
    else:
        conn = _sqlite_conn()
        try:
            row = conn.execute(
                "SELECT id, api_key, endpoint, status, n_smiles, n_processed, result_path, error, charge "
                "FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        except sqlite3.OperationalError:
            # Fallback for old schema without endpoint/charge
            row = conn.execute(
                "SELECT id, api_key, status, n_smiles, n_processed, result_path, error "
                "FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
            if row:
                row = (row[0], row[1], "/jobs", row[2], row[3], row[4], row[5], row[6], 0)
        conn.close()
        if not row:
            return None
        return {
            "id": row[0],
            "api_key": row[1],
            "endpoint": row[2],
            "status": row[3],
            "n_smiles": row[4],
            "n_processed": row[5],
            "result_path": row[6],
            "error": row[7],
            "charge": row[8] or 0,
        }


def _write_result(job_id: str, data: Any) -> Path:
    """Write task result to data/jobs/{job_id}.result.jsonl.

    Lists are written as one JSON line per item; other types as a single line.
    """
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = JOBS_DIR / f"{job_id}.result.jsonl"
    with out_path.open("w", encoding="utf-8") as out:
        if isinstance(data, list):
            for item in data:
                out.write(json.dumps(item) + "\n")
        else:
            out.write(json.dumps(data) + "\n")
    return out_path


def _refund_quota(job_id: str) -> None:
    """Refund the quota for a failed job."""
    try:
        info = _get_job_info(job_id)
        if not info:
            return
        api_key = info["api_key"]
        endpoint = info.get("endpoint", "/jobs")
        charge = info.get("charge", 0) or info.get("n_smiles", 0)
        if charge > 0:
            keysdb.record(api_key, f"{endpoint}/refund", -charge)
    except Exception:
        pass


def _send_webhook(job_id: str, status: str, error: str | None = None) -> None:
    """Best-effort webhook delivery on final failure or success."""
    try:
        info = _get_job_info(job_id)
        if not info:
            return
        api_key = info["api_key"]
        payload = {
            "job_id": job_id,
            "status": status,
            "n_processed": info.get("n_processed", 0),
        }
        if error:
            payload["error"] = error[:200]
        else:
            payload["result_url"] = f"/jobs/{job_id}/result"
        webhooks_out.deliver_async(api_key, f"job.{status}", payload)
    except Exception:
        pass


def _exponential_backoff(retries: int) -> int:
    """Return countdown seconds for exponential backoff: 60, 120, 240."""
    return 60 * (2 ** retries)


def _progress(job_id: str, processed: int, total: int, status: str) -> None:
    """Publish progress to Redis pub/sub + snapshot key, and update DB every 50 items."""
    redis_client.publish_progress_sync(job_id, processed, total, status)
    redis_client.store_progress_sync(job_id, processed, total, status)
    if processed % 50 == 0 or status in ("done", "failed"):
        _update_job_db(job_id, n_processed=processed, status=status)


def _finish(job_id: str, out_path: Path, n_processed: int, status: str = "done") -> None:
    """Mark a job as done and set result_path."""
    now = datetime.utcnow()
    if config.USE_POSTGRES:
        _update_job_db(
            job_id, status=status, n_processed=n_processed,
            result_path=str(out_path), finished_at=now,
        )
    else:
        _update_job_db(
            job_id, status=status, n_processed=n_processed,
            result_path=str(out_path), finished_at=now.isoformat(),
        )
    _send_webhook(job_id, status)


def _fail(job_id: str, error: str, refund: bool = True) -> None:
    """Mark a job as failed and optionally refund quota."""
    now = datetime.utcnow()
    if config.USE_POSTGRES:
        _update_job_db(job_id, status="failed", error=error[:500], finished_at=now)
    else:
        _update_job_db(job_id, status="failed", error=error[:500], finished_at=now.isoformat())
    if refund:
        _refund_quota(job_id)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def compute_batch_task(self, job_id: str, smiles: list[str], api_key: str):
    """Run compute.compute_molecule() for each SMILES in the batch.

    Idempotent: if the job is already done and the result file exists, returns
    the existing result without recomputing.
    """
    # Idempotency check
    info = _get_job_info(job_id)
    if info and info.get("status") == "done":
        result_path = info.get("result_path")
        if result_path and Path(result_path).exists():
            return {"job_id": job_id, "status": "done", "result_path": result_path}

    _update_job_db(job_id, status="running")
    redis_client.publish_progress_sync(job_id, 0, len(smiles), "running")

    try:
        total = len(smiles)
        results = []
        for i, smi in enumerate(smiles):
            r = compute.compute_molecule(cid=-(i + 1), smiles=smi)
            results.append(r.to_dict())
            if (i + 1) % 50 == 0:
                _progress(job_id, i + 1, total, "running")

        out_path = _write_result(job_id, results)
        _finish(job_id, out_path, len(results))
        return {"job_id": job_id, "status": "done", "result_path": str(out_path)}
    except Exception as exc:
        error = str(exc)[:500]
        if self.request.retries < 3:
            _fail(job_id, error, refund=False)  # Don't refund on retry
            raise self.retry(
                exc=exc,
                countdown=_exponential_backoff(self.request.retries),
            )
        _fail(job_id, error, refund=True)
        _send_webhook(job_id, "failed", error)
        raise


@app.task(bind=True, max_retries=3)
def predict_batch_task(self, job_id: str, smiles: list[str], api_key: str):
    """Run predict.predict_batch()."""
    info = _get_job_info(job_id)
    if info and info.get("status") == "done":
        result_path = info.get("result_path")
        if result_path and Path(result_path).exists():
            return {"job_id": job_id, "status": "done", "result_path": result_path}

    _update_job_db(job_id, status="running")
    redis_client.publish_progress_sync(job_id, 0, len(smiles), "running")

    try:
        results = predict.predict_batch(smiles)
        redis_client.publish_progress_sync(job_id, len(smiles), len(smiles), "running")
        out_path = _write_result(job_id, results)
        _finish(job_id, out_path, len(smiles))
        return {"job_id": job_id, "status": "done", "result_path": str(out_path)}
    except Exception as exc:
        error = str(exc)[:500]
        if self.request.retries < 3:
            _fail(job_id, error, refund=False)
            raise self.retry(
                exc=exc,
                countdown=_exponential_backoff(self.request.retries),
            )
        _fail(job_id, error, refund=True)
        _send_webhook(job_id, "failed", error)
        raise


@app.task(bind=True, max_retries=3)
def screen_batch_task(self, job_id: str, smiles: list[str], api_key: str):
    """Run screen.screen_batch()."""
    info = _get_job_info(job_id)
    if info and info.get("status") == "done":
        result_path = info.get("result_path")
        if result_path and Path(result_path).exists():
            return {"job_id": job_id, "status": "done", "result_path": result_path}

    _update_job_db(job_id, status="running")
    redis_client.publish_progress_sync(job_id, 0, len(smiles), "running")

    try:
        results = screen.screen_batch(smiles)
        redis_client.publish_progress_sync(job_id, len(smiles), len(smiles), "running")
        out_path = _write_result(job_id, results)
        _finish(job_id, out_path, len(smiles))
        return {"job_id": job_id, "status": "done", "result_path": str(out_path)}
    except Exception as exc:
        error = str(exc)[:500]
        if self.request.retries < 3:
            _fail(job_id, error, refund=False)
            raise self.retry(
                exc=exc,
                countdown=_exponential_backoff(self.request.retries),
            )
        _fail(job_id, error, refund=True)
        _send_webhook(job_id, "failed", error)
        raise


@app.task(bind=True, max_retries=3)
def similarity_search_task(self, job_id: str, query_smiles: str, top_k: int, api_key: str):
    """Run similarity.search() over the public SQLite dataset."""
    info = _get_job_info(job_id)
    if info and info.get("status") == "done":
        result_path = info.get("result_path")
        if result_path and Path(result_path).exists():
            return {"job_id": job_id, "status": "done", "result_path": result_path}

    _update_job_db(job_id, status="running")
    redis_client.publish_progress_sync(job_id, 0, 1, "running")

    try:
        conn = sqlite3.connect(str(config.DB_PATH))
        try:
            hits = similarity.search(conn, query_smiles, top_k=top_k)
        finally:
            conn.close()
        results = [h.to_dict() for h in hits]
        out_path = _write_result(job_id, results)
        _finish(job_id, out_path, 1)
        return {"job_id": job_id, "status": "done", "result_path": str(out_path)}
    except Exception as exc:
        error = str(exc)[:500]
        if self.request.retries < 3:
            _fail(job_id, error, refund=False)
            raise self.retry(
                exc=exc,
                countdown=_exponential_backoff(self.request.retries),
            )
        _fail(job_id, error, refund=True)
        _send_webhook(job_id, "failed", error)
        raise


@app.task(bind=True, max_retries=3)
def cluster_task(self, job_id: str, smiles: list[str], cutoff: float, api_key: str):
    """Run clustering.cluster()."""
    info = _get_job_info(job_id)
    if info and info.get("status") == "done":
        result_path = info.get("result_path")
        if result_path and Path(result_path).exists():
            return {"job_id": job_id, "status": "done", "result_path": result_path}

    _update_job_db(job_id, status="running")
    redis_client.publish_progress_sync(job_id, 0, len(smiles), "running")

    try:
        result = clustering.cluster(smiles, cutoff=cutoff)
        redis_client.publish_progress_sync(job_id, len(smiles), len(smiles), "running")
        out_path = _write_result(job_id, result.to_dict())
        _finish(job_id, out_path, len(smiles))
        return {"job_id": job_id, "status": "done", "result_path": str(out_path)}
    except Exception as exc:
        error = str(exc)[:500]
        if self.request.retries < 3:
            _fail(job_id, error, refund=False)
            raise self.retry(
                exc=exc,
                countdown=_exponential_backoff(self.request.retries),
            )
        _fail(job_id, error, refund=True)
        _send_webhook(job_id, "failed", error)
        raise


@app.task(bind=True, max_retries=3)
def conformer_generation_task(self, job_id: str, smiles: str, n_conformers: int, api_key: str):
    """Run conformers.generate()."""
    info = _get_job_info(job_id)
    if info and info.get("status") == "done":
        result_path = info.get("result_path")
        if result_path and Path(result_path).exists():
            return {"job_id": job_id, "status": "done", "result_path": result_path}

    _update_job_db(job_id, status="running")
    redis_client.publish_progress_sync(job_id, 0, 1, "running")

    try:
        result = conformers.generate(smiles, n_conformers=n_conformers)
        out_path = _write_result(job_id, result.to_dict())
        _finish(job_id, out_path, 1)
        return {"job_id": job_id, "status": "done", "result_path": str(out_path)}
    except Exception as exc:
        error = str(exc)[:500]
        if self.request.retries < 3:
            _fail(job_id, error, refund=False)
            raise self.retry(
                exc=exc,
                countdown=_exponential_backoff(self.request.retries),
            )
        _fail(job_id, error, refund=True)
        _send_webhook(job_id, "failed", error)
        raise


@app.task(bind=True, max_retries=3)
def fingerprint_batch_task(self, job_id: str, smiles: list[str], kind: str, n_bits: int, radius: int, api_key: str):
    """Run fingerprints.compute_one() for each SMILES."""
    info = _get_job_info(job_id)
    if info and info.get("status") == "done":
        result_path = info.get("result_path")
        if result_path and Path(result_path).exists():
            return {"job_id": job_id, "status": "done", "result_path": result_path}

    _update_job_db(job_id, status="running")
    redis_client.publish_progress_sync(job_id, 0, len(smiles), "running")

    try:
        results = [
            fingerprints.compute_one(s, kind=kind, n_bits=n_bits, radius=radius).to_dict()
            for s in smiles
        ]
        redis_client.publish_progress_sync(job_id, len(smiles), len(smiles), "running")
        out_path = _write_result(job_id, results)
        _finish(job_id, out_path, len(smiles))
        return {"job_id": job_id, "status": "done", "result_path": str(out_path)}
    except Exception as exc:
        error = str(exc)[:500]
        if self.request.retries < 3:
            _fail(job_id, error, refund=False)
            raise self.retry(
                exc=exc,
                countdown=_exponential_backoff(self.request.retries),
            )
        _fail(job_id, error, refund=True)
        _send_webhook(job_id, "failed", error)
        raise
