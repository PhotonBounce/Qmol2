"""SQLAlchemy 2.0 ORM models mirroring all existing SQLite schemas.

These models are used when USE_POSTGRES=true.  When false the legacy
SQLite modules (storage.py, keys.py, teams.py, jobs.py, audit.py) continue
to operate on raw sqlite3 connections.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass


class Molecule(Base):
    """Mirrors src/storage.py molecules table."""
    __tablename__ = "molecules"

    cid: Mapped[int] = mapped_column(Integer, primary_key=True)
    smiles: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[Optional[str]] = mapped_column(Text)
    basis: Mapped[Optional[str]] = mapped_column(Text)
    num_atoms: Mapped[Optional[int]] = mapped_column(Integer)
    num_heavy_atoms: Mapped[Optional[int]] = mapped_column(Integer)
    num_electrons: Mapped[Optional[int]] = mapped_column(Integer)
    num_qubits: Mapped[Optional[int]] = mapped_column(Integer)
    energy_hartree: Mapped[Optional[float]] = mapped_column(Float)
    homo_hartree: Mapped[Optional[float]] = mapped_column(Float)
    lumo_hartree: Mapped[Optional[float]] = mapped_column(Float)
    dipole_debye: Mapped[Optional[float]] = mapped_column(Float)
    mw: Mapped[Optional[float]] = mapped_column(Float)
    logp: Mapped[Optional[float]] = mapped_column(Float)
    tpsa: Mapped[Optional[float]] = mapped_column(Float)
    hbd: Mapped[Optional[int]] = mapped_column(Integer)
    hba: Mapped[Optional[int]] = mapped_column(Integer)
    rotatable_bonds: Mapped[Optional[int]] = mapped_column(Integer)
    ring_count: Mapped[Optional[int]] = mapped_column(Integer)
    aromatic_rings: Mapped[Optional[int]] = mapped_column(Integer)
    qed: Mapped[Optional[float]] = mapped_column(Float)
    ecfp4_hash: Mapped[Optional[str]] = mapped_column(Text)
    inchikey: Mapped[Optional[str]] = mapped_column(Text)
    murcko_scaffold: Mapped[Optional[str]] = mapped_column(Text)
    fsp3: Mapped[Optional[float]] = mapped_column(Float)
    heteroatom_count: Mapped[Optional[int]] = mapped_column(Integer)
    formal_charge: Mapped[Optional[int]] = mapped_column(Integer)
    stereo_centers: Mapped[Optional[int]] = mapped_column(Integer)
    mol_refractivity: Mapped[Optional[float]] = mapped_column(Float)
    lipinski_pass: Mapped[Optional[bool]] = mapped_column(Boolean)
    veber_pass: Mapped[Optional[bool]] = mapped_column(Boolean)
    pains_hit: Mapped[Optional[bool]] = mapped_column(Boolean)
    runtime_seconds: Mapped[Optional[float]] = mapped_column(Float)
    success: Mapped[Optional[bool]] = mapped_column(Boolean)
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_molecules_success", "success"),
        Index("idx_molecules_inchikey", "inchikey"),
        Index("idx_molecules_scaffold", "murcko_scaffold"),
    )


class ApiKey(Base):
    """Mirrors src/keys.py api_keys table + stripe_customer_id."""
    __tablename__ = "api_keys"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    tier: Mapped[str] = mapped_column(String(32), nullable=False)
    monthly_quota: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_api_keys_email", "email"),
        Index("idx_api_keys_active", "active"),
    )


class Usage(Base):
    """Mirrors src/keys.py usage table."""
    __tablename__ = "usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("api_keys.key", ondelete="CASCADE"),
        nullable=False,
    )
    endpoint: Mapped[Optional[str]] = mapped_column(String(255))
    smiles_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    ts: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_usage_key", "key"),
        Index("idx_usage_ts", "ts"),
    )


class Team(Base):
    """Mirrors src/teams.py teams table."""
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tier: Mapped[str] = mapped_column(String(32), nullable=False)
    monthly_quota: Mapped[int] = mapped_column(Integer, nullable=False)
    owner_email: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )


class TeamMember(Base):
    """Mirrors src/teams.py team_members table + role for future use."""
    __tablename__ = "team_members"

    team_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("teams.id", ondelete="CASCADE"),
        primary_key=True,
    )
    api_key: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("api_keys.key", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[Optional[str]] = mapped_column(String(32), default="member")
    added_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_team_members_team_id", "team_id"),
        Index("idx_team_members_api_key", "api_key"),
    )


class Job(Base):
    """Mirrors src/jobs.py jobs table."""
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    api_key: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("api_keys.key", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    n_smiles: Mapped[int] = mapped_column(Integer, nullable=False)
    n_processed: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    result_path: Mapped[Optional[str]] = mapped_column(Text)
    error: Mapped[Optional[str]] = mapped_column(Text)
    endpoint: Mapped[Optional[str]] = mapped_column(String(255), default="/jobs")
    charge: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    __table_args__ = (
        Index("idx_jobs_status", "status"),
        Index("idx_jobs_api_key", "api_key"),
        Index("idx_jobs_created_at", "created_at"),
        Index("idx_jobs_endpoint", "endpoint"),
    )


class AuditLog(Base):
    """Mirrors src/audit.py audit table."""
    __tablename__ = "audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("api_keys.key", ondelete="SET NULL"),
    )
    ip: Mapped[Optional[str]] = mapped_column(String(64))
    method: Mapped[Optional[str]] = mapped_column(String(16))
    path: Mapped[Optional[str]] = mapped_column(String(512))
    status: Mapped[Optional[int]] = mapped_column(Integer)
    ms: Mapped[Optional[int]] = mapped_column(Integer)
    n_smiles: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    extra: Mapped[Optional[str]] = mapped_column(Text)
    ts: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_audit_key", "api_key"),
        Index("idx_audit_ts", "ts"),
        Index("idx_audit_ip", "ip"),
    )


class Coupon(Base):
    """Mirrors src/coupons.py coupons table."""
    __tablename__ = "coupons"

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    percent_off: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    amount_off_cents: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    max_redemptions: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    redemptions: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    expires_at: Mapped[Optional[float]] = mapped_column(Float)
    tier_restriction: Mapped[Optional[str]] = mapped_column(String(32))
    attributed_ref_code: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )


class RefCode(Base):
    """Mirrors src/referrals.py ref_codes table."""
    __tablename__ = "ref_codes"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    api_key: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("api_keys.key", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )


class Referral(Base):
    """Mirrors src/referrals.py referrals table."""
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ref_code: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("ref_codes.code", ondelete="CASCADE"),
        nullable=False,
    )
    referred_email: Mapped[str] = mapped_column(String(255), nullable=False)
    tier: Mapped[str] = mapped_column(String(32), nullable=False)
    bonus_smiles: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    revenue_cents: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )


class Invoice(Base):
    """Persisted invoice records (src/invoices.py generates them on the fly;
    this table stores them for archival / customer-portal lookup)."""
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("api_keys.key", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    tier: Mapped[str] = mapped_column(String(32), nullable=False)
    period: Mapped[str] = mapped_column(String(16), nullable=False)  # YYYY-MM
    subtotal_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_smiles: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    total_calls: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    lines_json: Mapped[Optional[str]] = mapped_column(Text)  # JSON array of InvoiceLine
    status: Mapped[Optional[str]] = mapped_column(String(32), default="draft")
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_invoices_api_key", "api_key"),
        Index("idx_invoices_period", "period"),
    )
