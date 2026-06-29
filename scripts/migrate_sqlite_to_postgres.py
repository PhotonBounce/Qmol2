#!/usr/bin/env python3
"""One-time migration: SQLite -> PostgreSQL.

Reads:
  data/qmol.sqlite   -> molecules
  data/keys.sqlite   -> api_keys, usage, teams, team_members, audit,
                        coupons, ref_codes, referrals
  data/jobs.sqlite   -> jobs

Writes to PostgreSQL via asyncpg with batch inserts (1000 rows at a time).
Skips duplicates with ON CONFLICT DO NOTHING.

Usage:
  python scripts/migrate_sqlite_to_postgres.py [--dry-run]
"""
from __future__ import annotations
import argparse
import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Any, Sequence

import asyncpg
from tqdm import tqdm

import config

# ── Configuration ──────────────────────────────────────────────────
SQLITE_DB_PATHS = {
    "molecules": config.DB_PATH,
    "keys": config.KEYS_DB_PATH,
    "jobs": config.JOBS_DB_PATH,
}

STATE_PATH = config.DATA_DIR / "migration_state.json"
BATCH_SIZE = 1000

# Table specifications: (pg_table, sqlite_db_key, sqlite_table, columns, extra_defaults)
# Columns must match PostgreSQL schema names.
TABLE_SPECS: Sequence[tuple[str, str, str, list[str], dict[str, Any]]] = [
    # molecules
    (
        "molecules",
        "molecules",
        "molecules",
        [
            "cid", "smiles", "method", "basis", "num_atoms", "num_heavy_atoms",
            "num_electrons", "num_qubits", "energy_hartree", "homo_hartree",
            "lumo_hartree", "dipole_debye", "mw", "logp", "tpsa", "hbd", "hba",
            "rotatable_bonds", "ring_count", "aromatic_rings", "qed", "ecfp4_hash",
            "inchikey", "murcko_scaffold", "fsp3", "heteroatom_count",
            "formal_charge", "stereo_centers", "mol_refractivity",
            "lipinski_pass", "veber_pass", "pains_hit", "runtime_seconds",
            "success", "error", "created_at",
        ],
        {},
    ),
    # api_keys
    (
        "api_keys",
        "keys",
        "api_keys",
        ["key", "email", "tier", "monthly_quota", "active", "created_at"],
        {"stripe_customer_id": None},
    ),
    # usage
    (
        "usage",
        "keys",
        "usage",
        ["id", "key", "endpoint", "smiles_count", "ts"],
        {},
    ),
    # teams
    (
        "teams",
        "keys",
        "teams",
        ["id", "name", "tier", "monthly_quota", "owner_email", "created_at"],
        {},
    ),
    # team_members
    (
        "team_members",
        "keys",
        "team_members",
        ["team_id", "api_key", "added_at"],
        {"role": "member"},
    ),
    # jobs
    (
        "jobs",
        "jobs",
        "jobs",
        ["id", "api_key", "status", "n_smiles", "n_processed", "result_path", "error", "created_at", "finished_at"],
        {},
    ),
    # audit
    (
        "audit",
        "keys",
        "audit",
        ["id", "api_key", "ip", "method", "path", "status", "ms", "n_smiles", "extra", "ts"],
        {},
    ),
    # coupons
    (
        "coupons",
        "keys",
        "coupons",
        [
            "code", "percent_off", "amount_off_cents", "max_redemptions",
            "redemptions", "expires_at", "tier_restriction", "attributed_ref_code", "created_at",
        ],
        {},
    ),
    # ref_codes
    (
        "ref_codes",
        "keys",
        "ref_codes",
        ["code", "api_key", "created_at"],
        {},
    ),
    # referrals
    (
        "referrals",
        "keys",
        "referrals",
        ["id", "ref_code", "referred_email", "tier", "bonus_smiles", "revenue_cents", "created_at"],
        {},
    ),
]


# ── Helpers ──────────────────────────────────────────────────────
def _load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    return json.loads(STATE_PATH.read_text())


def _save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def _sqlite_conn(db_key: str) -> sqlite3.Connection:
    path = SQLITE_DB_PATHS[db_key]
    return sqlite3.connect(str(path))


def _build_insert_sql(table: str, columns: list[str]) -> str:
    cols = ", ".join(columns)
    placeholders = ", ".join(f"${i + 1}" for i in range(len(columns)))
    return f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"


async def _migrate_table(
    pg_pool: asyncpg.Pool,
    table: str,
    sqlite_db: str,
    sqlite_table: str,
    columns: list[str],
    defaults: dict[str, Any],
    dry_run: bool,
    state: dict[str, Any],
) -> int:
    """Migrate one table. Returns number of rows inserted."""
    offset = state.get(table, 0)
    conn = _sqlite_conn(sqlite_db)

    # Count total rows for tqdm
    total = conn.execute(
        f"SELECT COUNT(*) FROM {sqlite_table}"
    ).fetchone()[0]

    if offset >= total:
        print(f"  [{table}] already complete ({offset}/{total})")
        conn.close()
        return 0

    print(f"  [{table}] migrating {total - offset} rows (offset {offset})")

    all_pg_cols = columns + list(defaults.keys())
    insert_sql = _build_insert_sql(table, all_pg_cols)
    inserted = 0

    cursor = conn.execute(
        f"SELECT {', '.join(columns)} FROM {sqlite_table} ORDER BY rowid LIMIT -1 OFFSET ?",
        (offset,),
    )

    batch: list[tuple] = []
    pbar = tqdm(total=total, initial=offset, desc=table, unit="row")

    for row in cursor:
        row_dict = dict(zip(columns, row))
        # Convert SQLite booleans (0/1) to Python bools for PostgreSQL
        for col in columns:
            if col in ("active", "success", "lipinski_pass", "veber_pass", "pains_hit"):
                if row_dict[col] is not None:
                    row_dict[col] = bool(row_dict[col])
        # Add defaults
        for col, val in defaults.items():
            row_dict[col] = val
        batch.append(tuple(row_dict[c] for c in all_pg_cols))

        if len(batch) >= BATCH_SIZE:
            if not dry_run:
                await pg_pool.executemany(insert_sql, batch)
            inserted += len(batch)
            offset += len(batch)
            state[table] = offset
            _save_state(state)
            pbar.update(len(batch))
            batch = []

    if batch:
        if not dry_run:
            await pg_pool.executemany(insert_sql, batch)
        inserted += len(batch)
        offset += len(batch)
        state[table] = offset
        _save_state(state)
        pbar.update(len(batch))

    pbar.close()
    conn.close()
    print(f"  [{table}] done — {inserted} rows inserted")
    return inserted


async def _reset_sequences(pg_pool: asyncpg.Pool) -> None:
    """Reset SERIAL sequences after manual id inserts."""
    seq_tables = [
        ("usage", "id"),
        ("audit", "id"),
        ("referrals", "id"),
        ("invoices", "id"),
    ]
    for table, col in seq_tables:
        try:
            await pg_pool.execute(
                f"SELECT setval(pg_get_serial_sequence('{table}', '{col}'), COALESCE(MAX({col}), 0)) FROM {table}"
            )
        except Exception as exc:
            print(f"  [warn] could not reset sequence for {table}.{col}: {exc}")


async def main(dry_run: bool) -> None:
    print("=" * 60)
    print("Q-Mol SQLite -> PostgreSQL Migration")
    print(f"  PostgreSQL: {config.DATABASE_URL}")
    print(f"  dry_run:    {dry_run}")
    print("=" * 60)

    state = _load_state()
    total_inserted = 0

    pg_pool = await asyncpg.create_pool(
        dsn=config.DATABASE_URL.replace("+asyncpg", "").replace("postgresql+psycopg2", "postgresql"),
        min_size=1,
        max_size=5,
    )

    try:
        for table, sqlite_db, sqlite_table, columns, defaults in TABLE_SPECS:
            # Check if SQLite table exists
            conn = _sqlite_conn(sqlite_db)
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (sqlite_table,),
            )
            exists = cur.fetchone() is not None
            conn.close()
            if not exists:
                print(f"  [{table}] SQLite table '{sqlite_table}' not found — skipping")
                state[table] = 0
                _save_state(state)
                continue

            n = await _migrate_table(
                pg_pool, table, sqlite_db, sqlite_table, columns, defaults, dry_run, state
            )
            total_inserted += n

        if not dry_run:
            print("\nResetting SERIAL sequences...")
            await _reset_sequences(pg_pool)

    finally:
        await pg_pool.close()

    print("\n" + "=" * 60)
    print(f"Migration complete. Total rows inserted: {total_inserted}")
    print(f"State saved to: {STATE_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate SQLite to PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to PostgreSQL")
    args = parser.parse_args()
    asyncio.run(main(args.dry_run))
