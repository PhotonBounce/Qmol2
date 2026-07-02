from __future__ import annotations

import asyncio
import io
import os
import tarfile
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any

import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_user
from app.core.cache import get_cache, set_cache
from app.core.storage import (
    download_fileobj,
    get_presigned_download_url,
    get_presigned_upload_url,
    upload_fileobj,
)
from app.db.database import get_db
from app.monitoring import JOBS_CREATED_TOTAL
from app.models import Job, JobStatus, Transaction, TransactionType, User, WorkUnit, WorkUnitStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])

MAX_AGGREGATE_RESULTS_SIZE = 500 * 1024 * 1024  # 500 MB

# Regex for Docker image names (whitelist approach)
_DOCKER_IMAGE_RE = re.compile(r"^[a-z0-9._/-]+(:[a-z0-9._-]+)?$")

# Denylisted environment variable keys that could break sandboxing
_ENV_DENYLIST = {"LD_PRELOAD", "PATH", "HOME", "SHELL", "USER", "TMPDIR", "LD_LIBRARY_PATH"}

# Shell metacharacters that should not appear in commands
_COMMAND_FORBIDDEN = {";", "|", "&&", "||", "`", "$()", "${", ">", "<"}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class JobCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    docker_image: str = Field(min_length=1, max_length=255)
    command: str | None = None
    env_vars: dict[str, Any] = Field(default_factory=dict)
    input_files: list[str] = Field(default_factory=list)
    work_unit_count: int = Field(ge=1, le=10000)
    reward_per_unit: float = Field(ge=0.0, le=10000.0)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("name cannot be empty or whitespace only")
        if "\n" in stripped or "\r" in stripped:
            raise ValueError("name cannot contain newlines")
        return stripped

    @field_validator("docker_image")
    @classmethod
    def _validate_docker_image(cls, v: str) -> str:
        if not _DOCKER_IMAGE_RE.match(v):
            raise ValueError("docker_image contains invalid characters")
        return v

    @field_validator("command")
    @classmethod
    def _validate_command(cls, v: str | None) -> str | None:
        if v is None:
            return v
        for char in _COMMAND_FORBIDDEN:
            if char in v:
                raise ValueError(f"command contains forbidden shell metacharacter: {char}")
        return v

    @field_validator("env_vars")
    @classmethod
    def _validate_env_vars(cls, v: dict[str, Any]) -> dict[str, Any]:
        for key in v:
            if key.upper() in _ENV_DENYLIST:
                raise ValueError(f"env_vars key '{key}' is forbidden")
        return v


class WorkUnitResponse(BaseModel):
    id: uuid.UUID
    unit_index: int
    status: str
    assigned_worker_id: uuid.UUID | None
    result_artifact_url: str | None
    result_checksum: str | None
    started_at: datetime | None
    completed_at: datetime | None
    validated_at: datetime | None

    class Config:
        from_attributes = True


class JobResponse(BaseModel):
    id: uuid.UUID
    name: str
    docker_image: str
    command: str | None
    env_vars: dict[str, Any]
    input_files: list[str]
    status: str
    work_unit_count: int
    reward_per_unit: float
    created_at: datetime
    updated_at: datetime
    work_units: list[WorkUnitResponse] = []

    class Config:
        from_attributes = True


class JobDetailResponse(JobResponse):
    work_units: list[WorkUnitResponse]


class JobCreateResponse(BaseModel):
    job_id: uuid.UUID
    input_upload_urls: list[str]


class PaginatedJobsResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[JobResponse]


class ResultsDownloadResponse(BaseModel):
    download_url: str
    expires_in_seconds: int


class CancelResponse(BaseModel):
    cancelled_units: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobCreateResponse:
    total_cost = payload.work_unit_count * payload.reward_per_unit
    if current_user.credits_balance < total_cost:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits: need {total_cost}, have {current_user.credits_balance}",
        )

    current_user.credits_balance -= total_cost
    current_user.total_credits_spent += total_cost

    job = Job(
        user_id=current_user.id,
        name=payload.name,
        docker_image=payload.docker_image,
        command=payload.command,
        env_vars=payload.env_vars,
        input_files=payload.input_files,
        status=JobStatus.pending,
        work_unit_count=payload.work_unit_count,
        reward_per_unit=payload.reward_per_unit,
    )
    db.add(job)

    # Generate presigned upload URLs for input files (one per work unit or per input file)
    input_upload_urls: list[str] = []
    work_units = []
    for i in range(payload.work_unit_count):
        object_name = f"jobs/{job.id}/inputs/unit_{i}.tar.gz"
        url = get_presigned_upload_url(object_name, expiry=900)
        input_upload_urls.append(url)
        wu = WorkUnit(
            job_id=job.id,
            unit_index=i,
            status=WorkUnitStatus.pending,
            input_artifact_url=object_name,
        )
        work_units.append(wu)

    db.add_all(work_units)

    transaction = Transaction(
        user_id=current_user.id,
        amount=total_cost,
        type=TransactionType.job_payment,
        description=f"Job payment for {payload.name} ({payload.work_unit_count} work units)",
    )
    db.add(transaction)

    await db.commit()
    await db.refresh(job)

    # Increment Prometheus counter
    JOBS_CREATED_TOTAL.inc()

    return JobCreateResponse(job_id=job.id, input_upload_urls=input_upload_urls)


@router.get("", response_model=PaginatedJobsResponse)
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    created_after: datetime | None = Query(None, description="Filter jobs created after this ISO datetime"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedJobsResponse:
    # Cache job list results for 5 seconds to reduce DB load
    cache_key = f"job_list:{current_user.id}:{skip}:{limit}:{created_after.isoformat() if created_after else 'all'}"
    cached = await get_cache(cache_key)
    if cached:
        import json
        return PaginatedJobsResponse(**json.loads(cached))

    # Build base filter
    base_filter = Job.user_id == current_user.id
    if created_after is not None:
        base_filter = base_filter & (Job.created_at >= created_after)

    # Count total
    count_stmt = select(func.count(Job.id)).where(base_filter)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    # Fetch page with eager-loaded work_units to avoid N+1
    stmt = (
        select(Job)
        .where(base_filter)
        .order_by(Job.created_at.desc())
        .offset(skip)
        .limit(limit)
        .options(selectinload(Job.work_units))
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    response = PaginatedJobsResponse(total=total, skip=skip, limit=limit, items=items)
    await set_cache(cache_key, response.model_dump_json(), ttl=5)
    return response


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobDetailResponse:
    stmt = (
        select(Job)
        .where(Job.id == job_id, Job.user_id == current_user.id)
        .options(selectinload(Job.work_units))
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.get("/{job_id}/results", response_model=ResultsDownloadResponse)
async def get_job_results(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResultsDownloadResponse:
    stmt = select(Job).where(Job.id == job_id, Job.user_id == current_user.id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Aggregate completed work units into a tar.gz archive
    wu_stmt = select(WorkUnit).where(
        WorkUnit.job_id == job_id,
        WorkUnit.status.in_([WorkUnitStatus.completed, WorkUnitStatus.validated]),
    )
    wu_result = await db.execute(wu_stmt)
    completed_units = wu_result.scalars().all()

    if not completed_units:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed results available for this job",
        )

    archive_key = f"jobs/{job_id}/results/aggregated.tar.gz"

    # Use a temporary file on disk instead of memory buffer to avoid OOM
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".tar.gz")
    try:
        total_size = 0
        with os.fdopen(tmp_fd, "wb") as tmp_file, tarfile.open(fileobj=tmp_file, mode="w:gz") as tar:
            for unit in completed_units:
                if unit.result_artifact_url:
                    # result_artifact_url is the object key stored in MinIO
                    data = await asyncio.to_thread(download_fileobj, unit.result_artifact_url)
                    total_size += len(data)
                    if total_size > MAX_AGGREGATE_RESULTS_SIZE:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail="Aggregate results exceed maximum download size of 500 MB",
                        )
                    info = tarfile.TarInfo(name=f"unit_{unit.unit_index}/result.tar.gz")
                    info.size = len(data)
                    tar.addfile(info, io.BytesIO(data))

        with open(tmp_path, "rb") as upload_file:
            await asyncio.to_thread(upload_fileobj, archive_key, upload_file)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    download_url = get_presigned_download_url(archive_key, expiry=900)
    return ResultsDownloadResponse(download_url=download_url, expires_in_seconds=900)


@router.post("/{job_id}/cancel", response_model=CancelResponse)
async def cancel_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CancelResponse:
    stmt = select(Job).where(Job.id == job_id, Job.user_id == current_user.id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Cancel pending work units
    wu_stmt = select(WorkUnit).where(
        WorkUnit.job_id == job_id,
        WorkUnit.status.in_([WorkUnitStatus.pending, WorkUnitStatus.assigned]),
    )
    wu_result = await db.execute(wu_stmt)
    units_to_cancel = wu_result.scalars().all()

    cancelled = 0
    for unit in units_to_cancel:
        unit.status = WorkUnitStatus.failed
        cancelled += 1

    await db.commit()
    return CancelResponse(cancelled_units=cancelled)
