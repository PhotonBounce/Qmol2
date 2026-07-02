from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.core.job_status import update_job_status
from app.core.rate_limit import is_rate_limited
from app.core.storage import get_presigned_download_url, get_presigned_upload_url
from app.core.worker_manager import (
    assign_work_unit,
    get_worker_profile,
    heartbeat_worker,
    submit_work_result,
)
from app.core.validator import requeue_work_unit
from app.models import User, WorkUnit, WorkUnitStatus, Worker, WorkerStatus
from app.core.cache import get_cache, set_cache
from app.monitoring import WORK_UNITS_COMPLETED_TOTAL
from passlib.context import CryptContext

router = APIRouter(prefix="/workers", tags=["workers"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MAX_RESULT_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# ---------------------------------------------------------------------------
# Dependency to authenticate a worker by api_key
# ---------------------------------------------------------------------------
async def get_current_worker(
    request: Request,
    api_key: str = Form(None),
    db: AsyncSession = Depends(get_db),
) -> Worker:
    resolved_key = request.headers.get("X-Worker-API-Key") or api_key
    if not resolved_key:
        resolved_key = request.query_params.get("api_key")
    if not resolved_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )

    # Simple in-memory rate limit: 10 requests per minute per worker key prefix
    prefix = resolved_key[:8]
    if is_rate_limited(f"worker:{prefix}", limit=10, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Slow down.",
        )

    stmt = select(Worker).where(Worker.api_key_prefix == prefix)
    result = await db.execute(stmt)
    workers = result.scalars().all()
    for w in workers:
        # CPU-bound bcrypt in thread pool to avoid blocking the event loop
        if await asyncio.to_thread(pwd_context.verify, resolved_key, w.api_key_hashed):
            if w.status == WorkerStatus.banned:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Worker is banned",
                )
            return w
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid worker API key",
    )


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class HeartbeatRequest(BaseModel):
    worker_id: uuid.UUID
    status: WorkerStatus
    capabilities_snapshot: dict[str, Any] = Field(default_factory=dict)


class WorkUnitClaimResponse(BaseModel):
    work_unit_id: uuid.UUID
    job_id: uuid.UUID
    docker_image: str
    command: str | None
    env_vars: dict[str, Any]
    input_artifact_url: str


class HeartbeatResponse(BaseModel):
    message: str
    assigned_work_unit: WorkUnitClaimResponse | None = None


class ClaimUnitResponse(BaseModel):
    work_unit: WorkUnitClaimResponse | None


class SubmitResultResponse(BaseModel):
    status: str
    work_unit_id: uuid.UUID


class WorkerProfileResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    capabilities: dict[str, Any]
    reputation_score: float
    total_credits_earned: float
    pending_credits: float
    last_heartbeat: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedWorkersResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[WorkerProfileResponse]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post("/heartbeat", response_model=HeartbeatResponse)
async def worker_heartbeat(
    payload: HeartbeatRequest,
    db: AsyncSession = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
) -> HeartbeatResponse:
    if current_worker.id != payload.worker_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Worker ID mismatch")

    updated = await heartbeat_worker(db, payload.worker_id, payload.status)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")

    # If worker is online and not busy, try to assign a work unit
    assigned: WorkUnitClaimResponse | None = None
    if payload.status in (WorkerStatus.online, WorkerStatus.offline):
        # Only assign if they seem available
        wu = await assign_work_unit(db, payload.worker_id)
        if wu:
            # Refresh job relation
            await db.refresh(wu, ["job"])
            assigned = WorkUnitClaimResponse(
                work_unit_id=wu.id,
                job_id=wu.job_id,
                docker_image=wu.job.docker_image,
                command=wu.job.command,
                env_vars=wu.job.env_vars,
                input_artifact_url=get_presigned_download_url(wu.input_artifact_url, expiry=900),
            )

    return HeartbeatResponse(message="ok", assigned_work_unit=assigned)


@router.post("/claim-unit", response_model=ClaimUnitResponse)
async def worker_claim_unit(
    db: AsyncSession = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
) -> ClaimUnitResponse:
    wu = await assign_work_unit(db, current_worker.id)
    if wu is None:
        return ClaimUnitResponse(work_unit=None)

    await db.refresh(wu, ["job"])
    claim = WorkUnitClaimResponse(
        work_unit_id=wu.id,
        job_id=wu.job_id,
        docker_image=wu.job.docker_image,
        command=wu.job.command,
        env_vars=wu.job.env_vars,
        input_artifact_url=get_presigned_download_url(wu.input_artifact_url, expiry=900),
    )
    return ClaimUnitResponse(work_unit=claim)


@router.post("/submit-result", response_model=SubmitResultResponse)
async def worker_submit_result(
    work_unit_id: uuid.UUID = Form(...),
    checksum: str = Form(...),
    logs: str = Form(""),
    result_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
) -> SubmitResultResponse:
    # Verify work unit is assigned to this worker and running/assigned
    stmt = select(WorkUnit).where(
        WorkUnit.id == work_unit_id,
        WorkUnit.assigned_worker_id == current_worker.id,
    )
    result = await db.execute(stmt)
    wu = result.scalar_one_or_none()
    if wu is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work unit not found or not assigned to this worker",
        )

    if wu.status not in (WorkUnitStatus.assigned, WorkUnitStatus.running):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Work unit is in status {wu.status}, cannot submit result",
        )

    # Stream the uploaded file directly to MinIO without loading into RAM.
    # FastAPI's UploadFile exposes a SpooledTemporaryFile; we can pass it
    # directly to boto3's upload_fileobj which will read in chunks.
    object_key = f"jobs/{wu.job_id}/results/{wu.id}/result.tar.gz"

    # Validate size without reading everything into memory by seeking to end
    result_file.file.seek(0, 2)  # seek to end
    file_size = result_file.file.tell()
    result_file.file.seek(0)  # rewind
    if file_size > MAX_RESULT_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Result file exceeds maximum size of 50 MB",
        )

    # Validate magic bytes for gzip (tar.gz starts with \x1f\x8b)
    magic = result_file.file.read(2)
    result_file.file.seek(0)
    if magic != b"\x1f\x8b":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid gzip archive",
        )

    from app.core.storage import upload_fileobj
    await asyncio.to_thread(upload_fileobj, object_key, result_file.file)

    # Update work unit
    await submit_work_result(db, work_unit_id, object_key, checksum, logs)
    await update_job_status(db, wu.job_id)

    # Increment Prometheus counter
    WORK_UNITS_COMPLETED_TOTAL.inc()

    # Mark worker as online (no longer busy) if they have no other assigned units
    pending_stmt = select(WorkUnit).where(
        WorkUnit.assigned_worker_id == current_worker.id,
        WorkUnit.status.in_([WorkUnitStatus.assigned, WorkUnitStatus.running]),
    )
    pending_result = await db.execute(pending_stmt)
    if not pending_result.scalars().first():
        await db.execute(
            update(Worker)
            .where(Worker.id == current_worker.id)
            .values(status=WorkerStatus.online)
        )
        await db.commit()

    return SubmitResultResponse(status="received", work_unit_id=work_unit_id)


@router.get("/profile", response_model=WorkerProfileResponse)
async def worker_profile(
    db: AsyncSession = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
) -> WorkerProfileResponse:
    # Cache worker profile for 60 seconds to reduce DB hits
    cache_key = f"worker_profile:{current_worker.id}"
    cached = await get_cache(cache_key)
    if cached:
        import json
        return WorkerProfileResponse(**json.loads(cached))

    profile = await get_worker_profile(db, current_worker.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")

    response = WorkerProfileResponse.model_validate(profile)
    await set_cache(cache_key, response.model_dump_json(), ttl=60)
    return response


@router.get("", response_model=PaginatedWorkersResponse)
async def list_workers(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedWorkersResponse:
    # Cache worker list for 30 seconds to reduce DB load
    cache_key = f"worker_list:{skip}:{limit}"
    cached = await get_cache(cache_key)
    if cached:
        import json
        return PaginatedWorkersResponse(**json.loads(cached))

    count_stmt = select(func.count(Worker.id))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    stmt = (
        select(Worker)
        .order_by(Worker.last_heartbeat.desc().nullslast())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    response = PaginatedWorkersResponse(total=total, skip=skip, limit=limit, items=items)
    await set_cache(cache_key, response.model_dump_json(), ttl=30)
    return response
