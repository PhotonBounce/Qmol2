from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WorkUnit, WorkUnitStatus, Worker, WorkerStatus


async def register_worker(
    db: AsyncSession, name: str, capabilities: dict, api_key_hashed: str
) -> Worker:
    worker = Worker(
        name=name,
        capabilities=capabilities,
        api_key_hashed=api_key_hashed,
        status=WorkerStatus.online,
        last_heartbeat=datetime.now(timezone.utc),
    )
    db.add(worker)
    await db.commit()
    await db.refresh(worker)
    return worker


async def heartbeat_worker(
    db: AsyncSession, worker_id: uuid.UUID, status: WorkerStatus
) -> Worker | None:
    stmt = (
        update(Worker)
        .where(Worker.id == worker_id)
        .values(
            status=status,
            last_heartbeat=datetime.now(timezone.utc),
        )
        .returning(Worker)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one_or_none()


async def assign_work_unit(db: AsyncSession, worker_id: uuid.UUID) -> WorkUnit | None:
    """Assign the first pending work unit to the given worker."""
    # Find a pending work unit not yet assigned
    stmt = (
        select(WorkUnit)
        .where(
            WorkUnit.status == WorkUnitStatus.pending,
            WorkUnit.assigned_worker_id.is_(None),
        )
        .order_by(WorkUnit.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    result = await db.execute(stmt)
    work_unit: WorkUnit | None = result.scalar_one_or_none()
    if work_unit is None:
        return None

    work_unit.status = WorkUnitStatus.assigned
    work_unit.assigned_worker_id = worker_id
    work_unit.started_at = datetime.now(timezone.utc)

    # Mark worker as busy if they have assigned work
    await db.execute(
        update(Worker)
        .where(Worker.id == worker_id)
        .values(status=WorkerStatus.busy)
    )

    await db.commit()
    await db.refresh(work_unit)
    return work_unit


async def submit_work_result(
    db: AsyncSession,
    work_unit_id: uuid.UUID,
    result_url: str,
    checksum: str,
    logs: str,
) -> WorkUnit | None:
    stmt = (
        update(WorkUnit)
        .where(WorkUnit.id == work_unit_id)
        .values(
            status=WorkUnitStatus.completed,
            result_artifact_url=result_url,
            result_checksum=checksum,
            completed_at=datetime.now(timezone.utc),
        )
        .returning(WorkUnit)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one_or_none()


async def get_worker_profile(db: AsyncSession, worker_id: uuid.UUID) -> Worker | None:
    stmt = select(Worker).where(Worker.id == worker_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
