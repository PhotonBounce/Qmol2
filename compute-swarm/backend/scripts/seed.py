#!/usr/bin/env python3
"""
Seed the database with demo data for testing a fresh production deployment.

Usage (inside the API container):
    cd /app
    python scripts/seed.py

Or via Docker Compose:
    docker compose -f docker-compose.prod.yml exec api python scripts/seed.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory (backend/) to Python path so we can import `app`
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal, engine
from app.models import (
    Base,
    Job,
    JobStatus,
    User,
    UserRole,
    WorkUnit,
    WorkUnitStatus,
    Worker,
    WorkerStatus,
)
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed() -> None:
    """Create demo researcher, worker, job, and work units."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Check if demo data already exists
        existing = await db.execute(select(User).where(User.email == "demo@computeswarm.local"))
        if existing.scalar_one_or_none() is not None:
            print("Demo data already exists. Aborting.")
            return

        # --- Demo researcher --------------------------------------------------
        researcher = User(
            email="demo@computeswarm.local",
            hashed_password=pwd_context.hash("demo123"),
            role=UserRole.researcher,
            credits_balance=1000.0,
            total_credits_spent=0.0,
        )
        db.add(researcher)
        await db.flush()

        # --- Demo worker ------------------------------------------------------
        worker = Worker(
            name="demo-worker-01",
            api_key_hashed=pwd_context.hash("demo-api-key-12345"),
            api_key_prefix="demo-api",
            status=WorkerStatus.online,
            capabilities={
                "cpu_cores": 8,
                "ram_gb": 32,
                "os": "linux",
                "docker_version": "24.0.0",
            },
            reputation_score=1.0,
            total_credits_earned=0.0,
            pending_credits=0.0,
            last_heartbeat=datetime.now(timezone.utc),
        )
        db.add(worker)
        await db.flush()

        # --- Demo job ---------------------------------------------------------
        job = Job(
            user_id=researcher.id,
            name="Demo Molecular Simulation",
            docker_image="computeswarm/molecular-dock:latest",
            command="python /workspace/input/sim.py --output /workspace/output/result.npy",
            env_vars={"STEPS": "1000", "TEMPERATURE": "300"},
            input_files=[],
            status=JobStatus.pending,
            work_unit_count=4,
            reward_per_unit=10.0,
        )
        db.add(job)
        await db.flush()

        # --- Work units -------------------------------------------------------
        for i in range(4):
            wu = WorkUnit(
                job_id=job.id,
                unit_index=i,
                status=WorkUnitStatus.pending,
                input_artifact_url=f"jobs/{job.id}/inputs/unit_{i}.tar.gz",
            )
            db.add(wu)

        await db.commit()

        print("=== Demo Data Seeded ===")
        print(f"Researcher: {researcher.email}  |  password: demo123")
        print(f"Worker:     {worker.name}  |  API key: demo-api-key-12345")
        print(f"Job:        '{job.name}'  |  {job.work_unit_count} work units @ {job.reward_per_unit} credits each")
        print("")
        print("You can now log in to the dashboard and submit / claim jobs.")


if __name__ == "__main__":
    asyncio.run(seed())
