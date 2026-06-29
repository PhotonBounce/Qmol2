from fastapi import APIRouter, Header, HTTPException, Depends
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated
from pathlib import Path
import json
import asyncio

import config
from src import jobs, keys as keysdb, redis_client
from src.dependencies import require_api_key

router = APIRouter(tags=["jobs"])


class JobSubmitIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"smiles": ["CCO", "c1ccccc1"]}
        }
    )
    smiles: List[str] = Field(..., min_length=1, max_length=50000)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: List[str]) -> List[str]:
        from rdkit import Chem
        invalid = [s for s in v if Chem.MolFromSmiles(s) is None]
        if invalid:
            raise ValueError(f"Invalid SMILES: {invalid[:5]}")
        return v


@router.post("/jobs")
def job_submit(
    body: JobSubmitIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Submit a large batch. Returns job_id."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    n = len(body.smiles)
    used = keysdb.month_usage(x_api_key)
    if used + n > info.monthly_quota:
        raise HTTPException(status_code=402,
                            detail=f"Quota would be exceeded ({used}/{info.monthly_quota})")
    keysdb.record(x_api_key, "/jobs", n)
    job_id = jobs.submit(x_api_key, body.smiles, endpoint="/jobs", charge=n)
    return {"job_id": job_id, "status": "queued", "n_smiles": n}


@router.get("/jobs/{job_id}")
def job_status(
    job_id: str,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    if jobs.owner(job_id) != x_api_key:
        raise HTTPException(status_code=404, detail="Job not found")
    info = jobs.get(job_id)
    if not info:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": info.id, "status": info.status,
        "n_smiles": info.n_smiles, "n_processed": info.n_processed,
        "error": info.error,
        "result_url": f"/jobs/{info.id}/result" if info.status == "done" else None,
    }


@router.get("/jobs/{job_id}/result")
def job_result(
    job_id: str,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    if jobs.owner(job_id) != x_api_key:
        raise HTTPException(status_code=404, detail="Job not found")
    info = jobs.get(job_id)
    if not info or info.status != "done" or not info.result_path:
        raise HTTPException(status_code=409, detail=f"Job not ready (status={info.status if info else 'missing'})")
    # Critical bug fix: prevent path traversal by validating result_path is inside data/jobs
    result_path = Path(info.result_path).resolve()
    allowed_base = Path(config.DATA_DIR).resolve()
    if not str(result_path).startswith(str(allowed_base)):
        raise HTTPException(status_code=403, detail="Invalid result path")
    return FileResponse(result_path, media_type="application/x-jsonlines",
                        filename=f"{job_id}.jsonl")


@router.get("/jobs/{job_id}/stream")
async def job_stream(
    job_id: str,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Server-Sent Events streaming real-time job progress."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    if jobs.owner(job_id) != x_api_key:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        r = redis_client.get_redis()
        channel = f"job:{job_id}:progress"
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)
        try:
            snap = await redis_client.get_progress(job_id)
            if snap:
                yield f"data: {json.dumps(snap)}\n\n"
                if snap.get("status") in ("done", "failed"):
                    return
            while True:
                message = await pubsub.get_message(timeout=1.0)
                if message and message.get("type") == "message":
                    data = json.loads(message["data"])
                    yield f"data: {json.dumps(data)}\n\n"
                    if data.get("status") in ("done", "failed"):
                        break
                await asyncio.sleep(0.1)
        finally:
            await pubsub.unsubscribe(channel)
            try:
                await pubsub.close()
            except Exception:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.delete("/jobs/{job_id}")
def job_cancel(
    job_id: str,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Cancel a running job."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    if jobs.owner(job_id) != x_api_key:
        raise HTTPException(status_code=404, detail="Job not found")
    jobs.cancel(job_id)
    return {"job_id": job_id, "status": "cancelled"}
