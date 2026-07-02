from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone, timedelta

from celery import Celery
from celery.signals import task_prerun
from sqlalchemy import create_engine, func, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Job, JobStatus, Transaction, TransactionType, WorkUnit, WorkUnitStatus, Worker, WorkerStatus

celery_app = Celery(
    "compute_swarm",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.core.scheduler"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "dispatch-pending-work": {
            "task": "app.core.scheduler.dispatch_pending_work",
            "schedule": 5.0,
        },
        "validate-completed-work": {
            "task": "app.core.scheduler.validate_completed_work",
            "schedule": 30.0,
        },
        "check-worker-health": {
            "task": "app.core.scheduler.check_worker_health",
            "schedule": 30.0,
        },
    },
)

# Sync engine for Celery tasks (SQLAlchemy sync inside async app)
_sync_database_url = settings.database_url.replace("+asyncpg", "")
_sync_engine = create_engine(_sync_database_url, future=True)
SyncSessionLocal = sessionmaker(bind=_sync_engine)


def _requeue_work_unit_sync(db, work_unit_id: uuid.UUID) -> None:
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
    )
    db.execute(stmt)
    db.commit()


def _sync_update_job_status(db: Session, job_id: uuid.UUID) -> JobStatus | None:
    """Recompute and update aggregate job status from its work units (sync)."""
    stmt = select(WorkUnit).where(WorkUnit.job_id == job_id)
    result = db.execute(stmt)
    units = result.scalars().all()

    if not units:
        return None

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
        new_status = JobStatus.completed

    job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
    if job is None:
        return None
    if job.status == new_status:
        return new_status

    job.status = new_status
    job.updated_at = datetime.now(timezone.utc)
    db.commit()
    return new_status


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def dispatch_pending_work(self) -> None:
    """Safety net: requeue stuck assigned and hung running work units."""
    try:
        now = datetime.now(timezone.utc)
        stuck_threshold = now - timedelta(minutes=5)
        hung_threshold = now - timedelta(minutes=30)
        heartbeat_threshold = now - timedelta(minutes=2)

        with SyncSessionLocal() as db:
            # Quick count check to avoid wasted queries when nothing is pending
            pending_count = db.execute(
                select(func.count(WorkUnit.id)).where(WorkUnit.status == WorkUnitStatus.pending)
            ).scalar_one()
            if pending_count == 0:
                return

            # Stuck assigned units (>5 min)
            stmt = select(WorkUnit).where(
                WorkUnit.status == WorkUnitStatus.assigned,
                WorkUnit.started_at < stuck_threshold,
            )
            stuck_units = db.execute(stmt).scalars().all()

            for unit in stuck_units:
                _requeue_work_unit_sync(db, unit.id)
                if unit.assigned_worker_id:
                    worker = db.execute(
                        select(Worker).where(
                            Worker.id == unit.assigned_worker_id,
                            Worker.last_heartbeat < heartbeat_threshold,
                        )
                    ).scalar_one_or_none()
                    if worker:
                        worker.status = WorkerStatus.offline
                        db.commit()
                _sync_update_job_status(db, unit.job_id)

            # Hung running units (>30 min)
            stmt = select(WorkUnit).where(
                WorkUnit.status == WorkUnitStatus.running,
                WorkUnit.started_at < hung_threshold,
            )
            hung_units = db.execute(stmt).scalars().all()

            for unit in hung_units:
                _requeue_work_unit_sync(db, unit.id)
                if unit.assigned_worker_id:
                    worker = db.execute(
                        select(Worker).where(
                            Worker.id == unit.assigned_worker_id,
                            Worker.last_heartbeat < heartbeat_threshold,
                        )
                    ).scalar_one_or_none()
                    if worker:
                        worker.status = WorkerStatus.offline
                        db.commit()
                _sync_update_job_status(db, unit.job_id)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("dispatch_pending_work failed")
        raise


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def validate_completed_work(self) -> None:
    """Query completed work units and dispatch validation replicas."""
    try:
        now = datetime.now(timezone.utc)

        with SyncSessionLocal() as db:
            # Quick count check to avoid wasted queries when nothing needs validation
            completed_count = db.execute(
                select(func.count(WorkUnit.id)).where(
                    WorkUnit.status == WorkUnitStatus.completed,
                    WorkUnit.validated_at.is_(None),
                    WorkUnit.assigned_worker_id.is_not(None),
                )
            ).scalar_one()
            if completed_count == 0:
                return

            stmt = select(WorkUnit).where(
                WorkUnit.status == WorkUnitStatus.completed,
                WorkUnit.validated_at.is_(None),
                WorkUnit.assigned_worker_id.is_not(None),
            )
            units = db.execute(stmt).scalars().all()

            for unit in units:
                # TODO: Full validation by redundancy in V2
                # For MVP, auto-validate completed units that have a checksum
                if unit.result_checksum:
                    unit.status = WorkUnitStatus.validated
                    unit.validated_at = now
                    db.commit()

                    # Update worker credits
                    if unit.assigned_worker_id:
                        job = db.execute(select(Job).where(Job.id == unit.job_id)).scalar_one_or_none()
                        if job:
                            worker = db.execute(
                                select(Worker).where(Worker.id == unit.assigned_worker_id)
                            ).scalar_one_or_none()
                            if worker:
                                worker.total_credits_earned += job.reward_per_unit

                                transaction = Transaction(
                                    user_id=job.user_id,
                                    worker_id=unit.assigned_worker_id,
                                    amount=job.reward_per_unit,
                                    type=TransactionType.worker_payout,
                                    description=f"Worker payout for unit {unit.unit_index} in job {job.name}",
                                )
                                db.add(transaction)
                                db.commit()

                    # Update aggregate job status
                    new_status = _sync_update_job_status(db, unit.job_id)

                    # Notify researcher on job completion
                    if new_status == JobStatus.completed:
                        try:
                            job = db.execute(select(Job).where(Job.id == unit.job_id)).scalar_one_or_none()
                            if job:
                                user = db.execute(select(User).where(User.id == job.user_id)).scalar_one_or_none()
                                if user and user.email:
                                    import asyncio
                                    from app.core.email import notify_job_completed
                                    try:
                                        asyncio.run(notify_job_completed(user.email, job.name))
                                    except Exception:
                                        import logging
                                        logging.getLogger(__name__).exception("Failed to send job completion email")
                        except Exception:
                            import logging
                            logging.getLogger(__name__).exception("Email notification failed")
    except Exception:
        import logging
        logging.getLogger(__name__).exception("validate_completed_work failed")
        raise


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def check_worker_health(self) -> None:
    """Mark stale workers as offline and requeue their assigned work."""
    try:
        now = datetime.now(timezone.utc)
        stale_threshold = now - timedelta(seconds=120)

        with SyncSessionLocal() as db:
            # Quick count check to avoid wasted queries when all workers are healthy
            stale_count = db.execute(
                select(func.count(Worker.id)).where(
                    Worker.last_heartbeat < stale_threshold,
                    Worker.status != WorkerStatus.offline,
                )
            ).scalar_one()
            if stale_count == 0:
                # Still sweep non-terminal job statuses even if no stale workers
                active_job_count = db.execute(
                    select(func.count(Job.id)).where(Job.status.notin_([JobStatus.completed, JobStatus.failed]))
                ).scalar_one()
                if active_job_count == 0:
                    return

            # Find stale workers
            stmt = select(Worker).where(
                Worker.last_heartbeat < stale_threshold,
                Worker.status != WorkerStatus.offline,
            )
            stale_workers = db.execute(stmt).scalars().all()

            stale_worker_ids = [w.id for w in stale_workers]

            for worker in stale_workers:
                worker.status = WorkerStatus.offline
                db.commit()

            # Requeue assigned/running work for stale workers
            if stale_worker_ids:
                stmt = select(WorkUnit).where(
                    WorkUnit.assigned_worker_id.in_(stale_worker_ids),
                    WorkUnit.status.in_([WorkUnitStatus.assigned, WorkUnitStatus.running]),
                )
                units = db.execute(stmt).scalars().all()

                for unit in units:
                    _requeue_work_unit_sync(db, unit.id)
                    _sync_update_job_status(db, unit.job_id)

            # Sweep all non-terminal jobs to update status
            job_stmt = select(Job).where(Job.status.notin_([JobStatus.completed, JobStatus.failed]))
            jobs = db.execute(job_stmt).scalars().all()
            for job in jobs:
                _sync_update_job_status(db, job.id)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("check_worker_health failed")
        raise
