from __future__ import annotations

import uuid
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WorkUnit, WorkUnitStatus, Worker, WorkerStatus


async def validate_work_unit(db: AsyncSession, work_unit_id: uuid.UUID) -> str:
    """Compare checksums in validation_replicas and return a verdict."""
    stmt = select(WorkUnit).where(WorkUnit.id == work_unit_id)
    result = await db.execute(stmt)
    work_unit: WorkUnit | None = result.scalar_one_or_none()
    if work_unit is None:
        return "not_found"

    if not work_unit.validation_replicas:
        return "insufficient_replicas"

    # Count checksum occurrences across all replicas (including original)
    all_checksums = []
    if work_unit.result_checksum:
        all_checksums.append(work_unit.result_checksum)
    for replica in work_unit.validation_replicas:
        all_checksums.append(replica.get("result_checksum", ""))

    if not all_checksums:
        return "no_checksums"

    counts = Counter(all_checksums)
    most_common_checksum, count = counts.most_common(1)[0]

    # Determine majority (need at least 2 out of 3 for a 3-way comparison)
    if count >= 2:
        verdict = "valid"
    else:
        verdict = "invalid"

    # Update work unit status
    work_unit.status = WorkUnitStatus.validated if verdict == "valid" else WorkUnitStatus.failed
    work_unit.validated_at = datetime.now(timezone.utc)
    await db.commit()

    # Adjust reputation for all involved workers
    await _adjust_reputation_for_unit(db, work_unit, most_common_checksum, verdict)

    if verdict == "invalid":
        await requeue_work_unit(db, work_unit_id)

    return verdict


async def _adjust_reputation_for_unit(
    db: AsyncSession,
    work_unit: WorkUnit,
    majority_checksum: str,
    verdict: str,
) -> None:
    """Adjust worker reputation based on validation result."""
    # Map worker_id -> whether their checksum matched the majority
    worker_results: list[tuple[uuid.UUID | None, bool]] = []
    if work_unit.assigned_worker_id and work_unit.result_checksum:
        worker_results.append(
            (work_unit.assigned_worker_id, work_unit.result_checksum == majority_checksum)
        )
    for replica in work_unit.validation_replicas:
        worker_id = replica.get("worker_id")
        if worker_id:
            worker_results.append(
                (uuid.UUID(worker_id), replica.get("result_checksum") == majority_checksum)
            )

    for worker_id, matched in worker_results:
        if worker_id is None:
            continue
        delta = 0.05 if matched else -0.2
        stmt = (
            select(Worker)
            .where(Worker.id == worker_id)
            .with_for_update()
        )
        result = await db.execute(stmt)
        worker: Worker | None = result.scalar_one_or_none()
        if worker is None:
            continue

        new_score = max(0.0, min(1.0, worker.reputation_score + delta))
        new_status = WorkerStatus.banned if new_score < 0.5 else worker.status

        await db.execute(
            update(Worker)
            .where(Worker.id == worker_id)
            .values(reputation_score=new_score, status=new_status)
        )
    await db.commit()


async def requeue_work_unit(db: AsyncSession, work_unit_id: uuid.UUID) -> WorkUnit | None:
    """Reset a work unit to pending so it can be reassigned."""
    stmt = (
        update(WorkUnit)
        .where(WorkUnit.id == work_unit_id)
        .values(
            status=WorkUnitStatus.pending,
            assigned_worker_id=None,
            result_artifact_url=None,
            result_checksum=None,
            started_at=None,
            completed_at=None,
            validated_at=None,
            validation_replicas=[],
        )
        .returning(WorkUnit)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one_or_none()
