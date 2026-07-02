"""Harvest engine — collects computed molecules for dataset monetization.

Every molecule computed via the API is automatically stored here.
Over time, this database becomes a sellable asset to pharmaceutical companies.
"""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB = Path("data/harvest.sqlite")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS molecules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    smiles TEXT NOT NULL UNIQUE,
    inchikey TEXT,
    canonical_smiles TEXT,
    mw REAL,
    logp REAL,
    tpsa REAL,
    hbd INTEGER,
    hba INTEGER,
    qed REAL,
    lipinski_pass INTEGER,
    veber_pass INTEGER,
    pains_hit INTEGER,
    num_atoms INTEGER,
    num_heavy_atoms INTEGER,
    rotatable_bonds INTEGER,
    ring_count INTEGER,
    aromatic_rings INTEGER,
    fsp3 REAL,
    heteroatom_count INTEGER,
    formal_charge INTEGER,
    stereo_centers INTEGER,
    mol_refractivity REAL,
    source_endpoint TEXT,
    submitted_by TEXT,
    submitted_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_molecules_smiles ON molecules(smiles);
CREATE INDEX IF NOT EXISTS idx_molecules_inchikey ON molecules(inchikey);
CREATE INDEX IF NOT EXISTS idx_molecules_qed ON molecules(qed);
CREATE INDEX IF NOT EXISTS idx_molecules_logp ON molecules(logp);
CREATE INDEX IF NOT EXISTS idx_molecules_mw ON molecules(mw);
CREATE INDEX IF NOT EXISTS idx_molecules_lipinski ON molecules(lipinski_pass);
CREATE INDEX IF NOT EXISTS idx_molecules_pains ON molecules(pains_hit);
CREATE INDEX IF NOT EXISTS idx_molecules_source ON molecules(source_endpoint);

CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    molecule_count INTEGER,
    filter_criteria TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    exported_at TEXT,
    buyer_email TEXT,
    price_usd REAL,
    sold INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS market_intelligence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint TEXT,
    query_summary TEXT,
    frequency INTEGER DEFAULT 1,
    last_seen TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def _connect() -> sqlite3.Connection:
    DEFAULT_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DEFAULT_DB))
    conn.executescript(_SCHEMA)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def ingest(
    smiles: str,
    descriptors: dict[str, Any],
    source_endpoint: str = "/compute",
    submitted_by: str | None = None,
) -> bool:
    """Store a computed molecule in the harvest database. Returns True if new."""
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT id FROM molecules WHERE smiles = ?", (smiles,)
        )
        if cur.fetchone():
            conn.execute(
                "UPDATE molecules SET source_endpoint = ?, submitted_by = ? WHERE smiles = ?",
                (source_endpoint, _hash_key(submitted_by), smiles),
            )
            conn.commit()
            return False

        conn.execute(
            """INSERT INTO molecules (
                smiles, inchikey, canonical_smiles, mw, logp, tpsa, hbd, hba, qed,
                lipinski_pass, veber_pass, pains_hit, num_atoms, num_heavy_atoms,
                rotatable_bonds, ring_count, aromatic_rings, fsp3, heteroatom_count,
                formal_charge, stereo_centers, mol_refractivity, source_endpoint, submitted_by
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                smiles,
                descriptors.get("inchikey"),
                descriptors.get("smiles"),
                descriptors.get("mw"),
                descriptors.get("logp"),
                descriptors.get("tpsa"),
                descriptors.get("hbd"),
                descriptors.get("hba"),
                descriptors.get("qed"),
                int(descriptors.get("lipinski_pass", 0)),
                int(descriptors.get("veber_pass", 0)),
                int(descriptors.get("pains_hit", 0)),
                descriptors.get("num_atoms"),
                descriptors.get("num_heavy_atoms"),
                descriptors.get("rotatable_bonds"),
                descriptors.get("ring_count"),
                descriptors.get("aromatic_rings"),
                descriptors.get("fsp3"),
                descriptors.get("heteroatom_count"),
                descriptors.get("formal_charge"),
                descriptors.get("stereo_centers"),
                descriptors.get("mol_refractivity"),
                source_endpoint,
                _hash_key(submitted_by),
            ),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def _hash_key(api_key: str | None) -> str | None:
    """Anonymize API key by keeping only first 8 chars."""
    if not api_key:
        return None
    return api_key[:8] + "***"


def stats() -> dict[str, Any]:
    """Return harvest database statistics."""
    conn = _connect()
    try:
        total = conn.execute("SELECT COUNT(*) FROM molecules").fetchone()[0]
        unique_inchikey = conn.execute(
            "SELECT COUNT(DISTINCT inchikey) FROM molecules WHERE inchikey IS NOT NULL"
        ).fetchone()[0]
        lipinski_pass = conn.execute(
            "SELECT COUNT(*) FROM molecules WHERE lipinski_pass = 1"
        ).fetchone()[0]
        qed_good = conn.execute(
            "SELECT COUNT(*) FROM molecules WHERE qed >= 0.7"
        ).fetchone()[0]
        by_source = conn.execute(
            "SELECT source_endpoint, COUNT(*) FROM molecules GROUP BY source_endpoint"
        ).fetchall()
        last_7d = conn.execute(
            "SELECT COUNT(*) FROM molecules WHERE submitted_at >= datetime('now', '-7 days')"
        ).fetchone()[0]
        return {
            "total_molecules": total,
            "unique_by_inchikey": unique_inchikey,
            "lipinski_pass": lipinski_pass,
            "qed_good": qed_good,
            "by_source": {s: c for s, c in by_source},
            "last_7_days": last_7d,
            "db_path": str(DEFAULT_DB),
        }
    finally:
        conn.close()


def create_dataset(
    name: str,
    description: str,
    filter_sql: str,
    max_molecules: int = 10_000,
) -> dict[str, Any]:
    """Create a curated dataset from the harvest database."""
    conn = _connect()
    try:
        rows = conn.execute(
            f"SELECT smiles, mw, logp, tpsa, qed, lipinski_pass, veber_pass, pains_hit, inchikey "
            f"FROM molecules WHERE {filter_sql} "
            f"ORDER BY qed DESC LIMIT ?",
            (max_molecules,),
        ).fetchall()

        dataset_id = conn.execute(
            "INSERT INTO datasets (name, description, molecule_count, filter_criteria) VALUES (?, ?, ?, ?)",
            (name, description, len(rows), json.dumps({"sql": filter_sql, "limit": max_molecules})),
        ).lastrowid
        conn.commit()

        molecules = [
            {
                "smiles": r[0], "mw": r[1], "logp": r[2], "tpsa": r[3], "qed": r[4],
                "lipinski_pass": r[5], "veber_pass": r[6], "pains_hit": r[7], "inchikey": r[8],
            }
            for r in rows
        ]

        return {
            "dataset_id": dataset_id,
            "name": name,
            "description": description,
            "molecule_count": len(molecules),
            "molecules": molecules[:100],
            "price_usd": _price_for_dataset(len(molecules)),
        }
    finally:
        conn.close()


def _price_for_dataset(n: int) -> float:
    """Dynamic pricing based on dataset size."""
    if n < 100:
        return 99.0
    elif n < 1_000:
        return 299.0
    elif n < 10_000:
        return 999.0
    else:
        return 2999.0


def export_dataset_csv(dataset_id: int) -> str:
    """Export a dataset as CSV for delivery."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT name, filter_criteria FROM datasets WHERE id = ?", (dataset_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Dataset {dataset_id} not found")

        filter_criteria = json.loads(row[1])
        filter_sql = filter_criteria["sql"]
        limit = filter_criteria["limit"]

        rows = conn.execute(
            f"SELECT smiles, inchikey, mw, logp, tpsa, qed, hbd, hba, lipinski_pass, veber_pass, pains_hit "
            f"FROM molecules WHERE {filter_sql} ORDER BY qed DESC LIMIT ?",
            (limit,),
        ).fetchall()

        import csv, io
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow([
            "smiles", "inchikey", "mw", "logp", "tpsa", "qed",
            "hbd", "hba", "lipinski_pass", "veber_pass", "pains_hit"
        ])
        for r in rows:
            writer.writerow(r)

        return out.getvalue()
    finally:
        conn.close()


def record_market_intelligence(endpoint: str, query_summary: str) -> None:
    """Track what users are searching for (anonymized)."""
    conn = _connect()
    try:
        conn.execute(
            """INSERT INTO market_intelligence (endpoint, query_summary, frequency)
               VALUES (?, ?, 1)
               ON CONFLICT DO UPDATE SET frequency = frequency + 1, last_seen = CURRENT_TIMESTAMP""",
            (endpoint, query_summary),
        )
        conn.commit()
    finally:
        conn.close()
