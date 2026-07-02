"""Initial migration: create users, workers, jobs, work_units tables.

Revision ID: 001_initial_migration
Revises:
Create Date: 2024-06-30 00:00:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_initial_migration"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("credits_balance", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_credits_spent", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)

    op.create_table(
        "workers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("api_key_hashed", sa.String(255), nullable=False),
        sa.Column("api_key_prefix", sa.String(16), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("reputation_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("total_credits_earned", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("pending_credits", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workers_api_key_prefix", "workers", ["api_key_prefix"], unique=False)

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("docker_image", sa.String(255), nullable=False),
        sa.Column("command", sa.Text(), nullable=True),
        sa.Column("env_vars", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("input_files", sa.JSON(), nullable=False, server_default="'[]'"),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("work_unit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reward_per_unit", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"], unique=False)

    op.create_table(
        "work_units",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("unit_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("assigned_worker_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("input_artifact_url", sa.String(1024), nullable=False),
        sa.Column("result_artifact_url", sa.String(1024), nullable=True),
        sa.Column("result_checksum", sa.String(128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "validation_replicas", sa.JSON(), nullable=False, server_default="'[]'"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_worker_id"], ["workers.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_work_units_job_id", "work_units", ["job_id"], unique=False)
    op.create_index("ix_work_units_assigned_worker_id", "work_units", ["assigned_worker_id"], unique=False)

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("description", sa.String(512), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"], unique=False)
    op.create_index("ix_transactions_worker_id", "transactions", ["worker_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_transactions_worker_id", table_name="transactions")
    op.drop_index("ix_transactions_user_id", table_name="transactions")
    op.drop_table("transactions")

    op.drop_index("ix_work_units_assigned_worker_id", table_name="work_units")
    op.drop_index("ix_work_units_job_id", table_name="work_units")
    op.drop_table("work_units")

    op.drop_index("ix_jobs_user_id", table_name="jobs")
    op.drop_table("jobs")

    op.drop_index("ix_workers_api_key_prefix", table_name="workers")
    op.drop_table("workers")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
