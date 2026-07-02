from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_admin
from app.db.database import get_db
from app.models import Job, User, Worker, WorkerStatus, JobStatus, WorkUnit, WorkUnitStatus

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class AdminStatsResponse(BaseModel):
    total_users: int
    total_workers: int
    total_jobs: int
    total_credits_in_circulation: float


class AdminWorkerResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    reputation_score: float
    total_credits_earned: float
    pending_credits: float
    last_heartbeat: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class AdminWorkersListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[AdminWorkerResponse]


class AdminJobResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    user_id: uuid.UUID
    work_unit_count: int
    reward_per_unit: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AdminJobsListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[AdminJobResponse]


class AdminUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    credits_balance: float
    total_credits_spent: float
    created_at: datetime

    class Config:
        from_attributes = True


class AdminUsersListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[AdminUserResponse]


class BanUnbanResponse(BaseModel):
    worker_id: uuid.UUID
    status: str
    action: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.get("/stats", response_model=AdminStatsResponse)
async def admin_stats(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> AdminStatsResponse:
    total_users = (
        await db.execute(select(func.count(User.id)))
    ).scalar_one() or 0

    total_workers = (
        await db.execute(select(func.count(Worker.id)))
    ).scalar_one() or 0

    total_jobs = (
        await db.execute(select(func.count(Job.id)))
    ).scalar_one() or 0

    total_credits = (
        await db.execute(select(func.sum(User.credits_balance)))
    ).scalar_one() or 0.0

    total_credits += (
        await db.execute(select(func.sum(Worker.total_credits_earned)))
    ).scalar_one() or 0.0

    return AdminStatsResponse(
        total_users=total_users,
        total_workers=total_workers,
        total_jobs=total_jobs,
        total_credits_in_circulation=round(total_credits, 2),
    )


@router.get("/workers", response_model=AdminWorkersListResponse)
async def admin_list_workers(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> AdminWorkersListResponse:
    count_stmt = select(func.count(Worker.id))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one() or 0

    stmt = (
        select(Worker)
        .order_by(Worker.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    return AdminWorkersListResponse(
        total=total, skip=skip, limit=limit, items=items
    )


@router.post("/workers/{worker_id}/ban", response_model=BanUnbanResponse)
async def admin_ban_worker(
    worker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> BanUnbanResponse:
    stmt = select(Worker).where(Worker.id == worker_id)
    result = await db.execute(stmt)
    worker = result.scalar_one_or_none()
    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found"
        )

    worker.status = WorkerStatus.banned
    await db.commit()
    await db.refresh(worker)
    return BanUnbanResponse(
        worker_id=worker.id, status=worker.status.value, action="banned"
    )


@router.post("/workers/{worker_id}/unban", response_model=BanUnbanResponse)
async def admin_unban_worker(
    worker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> BanUnbanResponse:
    stmt = select(Worker).where(Worker.id == worker_id)
    result = await db.execute(stmt)
    worker = result.scalar_one_or_none()
    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found"
        )

    # Set to offline; they must heartbeat to become online again.
    worker.status = WorkerStatus.offline
    await db.commit()
    await db.refresh(worker)
    return BanUnbanResponse(
        worker_id=worker.id, status=worker.status.value, action="unbanned"
    )


@router.get("/jobs", response_model=AdminJobsListResponse)
async def admin_list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> AdminJobsListResponse:
    count_stmt = select(func.count(Job.id))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one() or 0

    stmt = (
        select(Job)
        .order_by(Job.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    return AdminJobsListResponse(total=total, skip=skip, limit=limit, items=items)


@router.get("/users", response_model=AdminUsersListResponse)
async def admin_list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> AdminUsersListResponse:
    count_stmt = select(func.count(User.id))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one() or 0

    stmt = (
        select(User)
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    return AdminUsersListResponse(total=total, skip=skip, limit=limit, items=items)
