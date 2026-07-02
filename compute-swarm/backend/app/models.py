from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class UserRole(str, enum.Enum):
    researcher = "researcher"
    admin = "admin"


class WorkerStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    busy = "busy"
    banned = "banned"


class JobStatus(str, enum.Enum):
    pending = "pending"
    assigned = "assigned"
    running = "running"
    completed = "completed"
    failed = "failed"
    validating = "validating"


class WorkUnitStatus(str, enum.Enum):
    pending = "pending"
    assigned = "assigned"
    running = "running"
    completed = "completed"
    failed = "failed"
    validated = "validated"


class TransactionType(str, enum.Enum):
    credit_purchase = "credit_purchase"
    job_payment = "job_payment"
    worker_payout = "worker_payout"
    refund = "refund"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False), nullable=False, default=UserRole.researcher
    )
    credits_balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_credits_spent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    jobs: Mapped[list["Job"]] = relationship(
        "Job", back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )


class Worker(Base):
    __tablename__ = "workers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_hashed: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    status: Mapped[WorkerStatus] = mapped_column(
        Enum(WorkerStatus, native_enum=False), nullable=False, default=WorkerStatus.offline
    )
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    reputation_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    total_credits_earned: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    pending_credits: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    last_heartbeat: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    assigned_work_units: Mapped[list["WorkUnit"]] = relationship(
        "WorkUnit",
        back_populates="assigned_worker",
        foreign_keys="WorkUnit.assigned_worker_id",
        lazy="selectin",
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    docker_image: Mapped[str] = mapped_column(String(255), nullable=False)
    command: Mapped[str | None] = mapped_column(Text, nullable=True)
    env_vars: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    input_files: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False), nullable=False, default=JobStatus.pending
    )
    work_unit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reward_per_unit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="jobs", lazy="raise")
    work_units: Mapped[list["WorkUnit"]] = relationship(
        "WorkUnit", back_populates="job", lazy="selectin", cascade="all, delete-orphan"
    )


class WorkUnit(Base):
    __tablename__ = "work_units"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False, index=True
    )
    unit_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[WorkUnitStatus] = mapped_column(
        Enum(WorkUnitStatus, native_enum=False), nullable=False, default=WorkUnitStatus.pending, index=True
    )
    assigned_worker_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workers.id"), nullable=True, index=True
    )
    input_artifact_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    result_artifact_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    result_checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    validation_replicas: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    job: Mapped["Job"] = relationship("Job", back_populates="work_units", lazy="raise")
    assigned_worker: Mapped["Worker | None"] = relationship(
        "Worker",
        back_populates="assigned_work_units",
        foreign_keys="WorkUnit.assigned_worker_id",
        lazy="selectin",
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    worker_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workers.id"), nullable=True, index=True
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, native_enum=False), nullable=False
    )
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
