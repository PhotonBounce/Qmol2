from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, JobStatus, WorkUnit, WorkUnitStatus


async def update_job_status(db: AsyncSession, job_id: uuid.UUID) -> None:
    """Recompute and update aggregate job status from its work units."""
    result = await db.execute(
        select(WorkUnit).where(WorkUnit.job_id == job_id)
    )
    units = result.scalars().all()

    if not units:
        return

    statuses = {u.status for u in units}

    if statuses == {WorkUnitStatus.validated}:
        new_status = JobStatus.completed
    elif statuses == {WorkUnitStatus.failed}:
        new_status = JobStatus.failed
    elif WorkUnitStatus.running in statuses:
        new_status = JobStatus.running
    elif WorkUnitStatus.assigned in statuses:
        new_status = JobStatus.assigned
    elif WorkUnitStatus.pending in statuses:
        new_status = JobStatus.pending
    elif WorkUnitStatus.completed in statuses:
        new_status = JobStatus.validating
    else:
        # Mix of validated / failed
        new_status = JobStatus.completed

    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if job is None or job.status == new_status:
        return

    job.status = new_status
    job.updated_at = datetime.now(timezone.utc)
    await db.commit()
