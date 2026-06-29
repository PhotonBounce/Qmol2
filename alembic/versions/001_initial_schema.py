"""Initial schema — creates all tables from src/models.py.

Revision ID: 001
Revises: 
Create Date: 2025-06-29 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── api_keys (no FK) ──────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("tier", sa.String(32), nullable=False),
        sa.Column("monthly_quota", sa.Integer, nullable=False),
        sa.Column("active", sa.Boolean, default=True),
        sa.Column("stripe_customer_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_api_keys_email", "api_keys", ["email"])
    op.create_index("idx_api_keys_active", "api_keys", ["active"])

    # ── teams (no FK) ─────────────────────────────────────────────────
    op.create_table(
        "teams",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("tier", sa.String(32), nullable=False),
        sa.Column("monthly_quota", sa.Integer, nullable=False),
        sa.Column("owner_email", sa.String(255)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── molecules (no FK) ─────────────────────────────────────────────
    op.create_table(
        "molecules",
        sa.Column("cid", sa.Integer, primary_key=True),
        sa.Column("smiles", sa.Text, nullable=False),
        sa.Column("method", sa.Text),
        sa.Column("basis", sa.Text),
        sa.Column("num_atoms", sa.Integer),
        sa.Column("num_heavy_atoms", sa.Integer),
        sa.Column("num_electrons", sa.Integer),
        sa.Column("num_qubits", sa.Integer),
        sa.Column("energy_hartree", sa.Float),
        sa.Column("homo_hartree", sa.Float),
        sa.Column("lumo_hartree", sa.Float),
        sa.Column("dipole_debye", sa.Float),
        sa.Column("mw", sa.Float),
        sa.Column("logp", sa.Float),
        sa.Column("tpsa", sa.Float),
        sa.Column("hbd", sa.Integer),
        sa.Column("hba", sa.Integer),
        sa.Column("rotatable_bonds", sa.Integer),
        sa.Column("ring_count", sa.Integer),
        sa.Column("aromatic_rings", sa.Integer),
        sa.Column("qed", sa.Float),
        sa.Column("ecfp4_hash", sa.Text),
        sa.Column("inchikey", sa.Text),
        sa.Column("murcko_scaffold", sa.Text),
        sa.Column("fsp3", sa.Float),
        sa.Column("heteroatom_count", sa.Integer),
        sa.Column("formal_charge", sa.Integer),
        sa.Column("stereo_centers", sa.Integer),
        sa.Column("mol_refractivity", sa.Float),
        sa.Column("lipinski_pass", sa.Boolean),
        sa.Column("veber_pass", sa.Boolean),
        sa.Column("pains_hit", sa.Boolean),
        sa.Column("runtime_seconds", sa.Float),
        sa.Column("success", sa.Boolean),
        sa.Column("error", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_molecules_success", "molecules", ["success"])
    op.create_index("idx_molecules_inchikey", "molecules", ["inchikey"])
    op.create_index("idx_molecules_scaffold", "molecules", ["murcko_scaffold"])

    # ── usage (FK -> api_keys) ────────────────────────────────────────
    op.create_table(
        "usage",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "key",
            sa.String(64),
            sa.ForeignKey("api_keys.key", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("endpoint", sa.String(255)),
        sa.Column("smiles_count", sa.Integer, default=0),
        sa.Column("ts", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_usage_key", "usage", ["key"])
    op.create_index("idx_usage_ts", "usage", ["ts"])

    # ── team_members (FK -> teams, api_keys) ──────────────────────────
    op.create_table(
        "team_members",
        sa.Column(
            "team_id",
            sa.String(32),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "api_key",
            sa.String(64),
            sa.ForeignKey("api_keys.key", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(32), default="member"),
        sa.Column("added_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_team_members_team_id", "team_members", ["team_id"])
    op.create_index("idx_team_members_api_key", "team_members", ["api_key"])

    # ── jobs (FK -> api_keys) ─────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "api_key",
            sa.String(64),
            sa.ForeignKey("api_keys.key", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("n_smiles", sa.Integer, nullable=False),
        sa.Column("n_processed", sa.Integer, default=0),
        sa.Column("result_path", sa.Text),
        sa.Column("error", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime),
    )
    op.create_index("idx_jobs_status", "jobs", ["status"])
    op.create_index("idx_jobs_api_key", "jobs", ["api_key"])
    op.create_index("idx_jobs_created_at", "jobs", ["created_at"])

    # ── audit (FK -> api_keys) ───────────────────────────────────────
    op.create_table(
        "audit",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "api_key",
            sa.String(64),
            sa.ForeignKey("api_keys.key", ondelete="SET NULL"),
        ),
        sa.Column("ip", sa.String(64)),
        sa.Column("method", sa.String(16)),
        sa.Column("path", sa.String(512)),
        sa.Column("status", sa.Integer),
        sa.Column("ms", sa.Integer),
        sa.Column("n_smiles", sa.Integer, default=0),
        sa.Column("extra", sa.Text),
        sa.Column("ts", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_audit_key", "audit", ["api_key"])
    op.create_index("idx_audit_ts", "audit", ["ts"])
    op.create_index("idx_audit_ip", "audit", ["ip"])

    # ── coupons (no FK) ───────────────────────────────────────────────
    op.create_table(
        "coupons",
        sa.Column("code", sa.String(64), primary_key=True),
        sa.Column("percent_off", sa.Integer, default=0),
        sa.Column("amount_off_cents", sa.Integer, default=0),
        sa.Column("max_redemptions", sa.Integer, default=0),
        sa.Column("redemptions", sa.Integer, default=0),
        sa.Column("expires_at", sa.Float),
        sa.Column("tier_restriction", sa.String(32)),
        sa.Column("attributed_ref_code", sa.String(64)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── ref_codes (FK -> api_keys) ────────────────────────────────────
    op.create_table(
        "ref_codes",
        sa.Column("code", sa.String(32), primary_key=True),
        sa.Column(
            "api_key",
            sa.String(64),
            sa.ForeignKey("api_keys.key", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── referrals (FK -> ref_codes) ───────────────────────────────────
    op.create_table(
        "referrals",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "ref_code",
            sa.String(32),
            sa.ForeignKey("ref_codes.code", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("referred_email", sa.String(255), nullable=False),
        sa.Column("tier", sa.String(32), nullable=False),
        sa.Column("bonus_smiles", sa.Integer, default=0),
        sa.Column("revenue_cents", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── invoices (FK -> api_keys) ─────────────────────────────────────
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "api_key",
            sa.String(64),
            sa.ForeignKey("api_keys.key", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("tier", sa.String(32), nullable=False),
        sa.Column("period", sa.String(16), nullable=False),
        sa.Column("subtotal_cents", sa.Integer, nullable=False, default=0),
        sa.Column("total_smiles", sa.Integer, default=0),
        sa.Column("total_calls", sa.Integer, default=0),
        sa.Column("lines_json", sa.Text),
        sa.Column("status", sa.String(32), default="draft"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_invoices_api_key", "invoices", ["api_key"])
    op.create_index("idx_invoices_period", "invoices", ["period"])


def downgrade() -> None:
    op.drop_table("invoices")
    op.drop_table("referrals")
    op.drop_table("ref_codes")
    op.drop_table("coupons")
    op.drop_table("audit")
    op.drop_table("jobs")
    op.drop_table("team_members")
    op.drop_table("usage")
    op.drop_table("molecules")
    op.drop_table("teams")
    op.drop_table("api_keys")
