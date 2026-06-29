"""Collections service: named molecule folders with sharing and export.

Uses raw SQLite for default operation; SQLAlchemy models in src/models.py
mirror the schema for PostgreSQL mode.
"""
from __future__ import annotations
import io
import json
import sqlite3
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional

from src import keys as keysdb

DEFAULT_DB = Path("data/collections.sqlite")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS collections (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner_key TEXT NOT NULL,
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    is_public INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_collections_owner_key ON collections(owner_key);

CREATE TABLE IF NOT EXISTS collection_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id TEXT NOT NULL,
    smiles TEXT NOT NULL,
    name TEXT,
    notes TEXT,
    properties TEXT,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_collection_items_collection_id ON collection_items(collection_id);

CREATE TABLE IF NOT EXISTS collection_shares (
    collection_id TEXT NOT NULL,
    shared_with_key TEXT NOT NULL,
    role TEXT DEFAULT 'viewer',
    shared_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (collection_id, shared_with_key),
    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
);
"""


@dataclass
class CollectionInfo:
    id: str
    name: str
    owner_key: str
    description: str | None
    created_at: str
    is_public: bool

    def to_dict(self) -> dict:
        d = asdict(self)
        d["is_public"] = bool(d["is_public"])
        return d


@dataclass
class CollectionItemInfo:
    id: int
    collection_id: str
    smiles: str
    name: str | None
    notes: str | None
    properties: dict | None
    added_at: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["properties"] = d["properties"] or {}
        return d


def _connect() -> sqlite3.Connection:
    DEFAULT_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DEFAULT_DB))
    conn.executescript(_SCHEMA)
    conn.row_factory = sqlite3.Row
    return conn


def _generate_id() -> str:
    return str(uuid.uuid4())


def create_collection(owner_key: str, name: str, description: str | None = None, is_public: bool = False) -> CollectionInfo:
    conn = _connect()
    cid = _generate_id()
    conn.execute(
        "INSERT INTO collections (id, name, owner_key, description, is_public) VALUES (?,?,?,?,?)",
        (cid, name, owner_key, description, int(is_public)),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM collections WHERE id=?", (cid,)).fetchone()
    conn.close()
    return CollectionInfo(
        id=row["id"], name=row["name"], owner_key=row["owner_key"],
        description=row["description"], created_at=row["created_at"],
        is_public=bool(row["is_public"]),
    )


def list_collections(owner_key: str) -> list[CollectionInfo]:
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM collections WHERE owner_key=? ORDER BY created_at DESC",
        (owner_key,),
    ).fetchall()
    # Also include shared collections
    shared = conn.execute(
        "SELECT c.* FROM collections c JOIN collection_shares s ON c.id=s.collection_id WHERE s.shared_with_key=?",
        (owner_key,),
    ).fetchall()
    conn.close()
    seen = set()
    results = []
    for row in list(rows) + list(shared):
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        results.append(CollectionInfo(
            id=row["id"], name=row["name"], owner_key=row["owner_key"],
            description=row["description"], created_at=row["created_at"],
            is_public=bool(row["is_public"]),
        ))
    return results


def get_collection(collection_id: str) -> CollectionInfo | None:
    conn = _connect()
    row = conn.execute("SELECT * FROM collections WHERE id=?", (collection_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return CollectionInfo(
        id=row["id"], name=row["name"], owner_key=row["owner_key"],
        description=row["description"], created_at=row["created_at"],
        is_public=bool(row["is_public"]),
    )


def get_collection_items(collection_id: str) -> list[CollectionItemInfo]:
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM collection_items WHERE collection_id=? ORDER BY added_at DESC",
        (collection_id,),
    ).fetchall()
    conn.close()
    return [
        CollectionItemInfo(
            id=row["id"], collection_id=row["collection_id"], smiles=row["smiles"],
            name=row["name"], notes=row["notes"],
            properties=json.loads(row["properties"]) if row["properties"] else None,
            added_at=row["added_at"],
        )
        for row in rows
    ]


def add_item(collection_id: str, smiles: str, name: str | None = None,
             notes: str | None = None, properties: dict | None = None) -> CollectionItemInfo:
    conn = _connect()
    props = json.dumps(properties) if properties else None
    cur = conn.execute(
        "INSERT INTO collection_items (collection_id, smiles, name, notes, properties) VALUES (?,?,?,?,?)",
        (collection_id, smiles, name, notes, props),
    )
    item_id = cur.lastrowid
    conn.commit()
    row = conn.execute("SELECT * FROM collection_items WHERE id=?", (item_id,)).fetchone()
    conn.close()
    return CollectionItemInfo(
        id=row["id"], collection_id=row["collection_id"], smiles=row["smiles"],
        name=row["name"], notes=row["notes"],
        properties=json.loads(row["properties"]) if row["properties"] else None,
        added_at=row["added_at"],
    )


def remove_item(collection_id: str, item_id: int) -> bool:
    conn = _connect()
    cur = conn.execute(
        "DELETE FROM collection_items WHERE collection_id=? AND id=?",
        (collection_id, item_id),
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def update_collection(collection_id: str, name: str | None = None,
                      description: str | None = None, is_public: bool | None = None) -> CollectionInfo | None:
    conn = _connect()
    updates = []
    params = []
    if name is not None:
        updates.append("name=?")
        params.append(name)
    if description is not None:
        updates.append("description=?")
        params.append(description)
    if is_public is not None:
        updates.append("is_public=?")
        params.append(int(is_public))
    if not updates:
        conn.close()
        return get_collection(collection_id)
    params.append(collection_id)
    conn.execute(f"UPDATE collections SET {', '.join(updates)} WHERE id=?", params)
    conn.commit()
    row = conn.execute("SELECT * FROM collections WHERE id=?", (collection_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return CollectionInfo(
        id=row["id"], name=row["name"], owner_key=row["owner_key"],
        description=row["description"], created_at=row["created_at"],
        is_public=bool(row["is_public"]),
    )


def delete_collection(collection_id: str) -> bool:
    conn = _connect()
    cur = conn.execute("DELETE FROM collections WHERE id=?", (collection_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def share_collection(collection_id: str, shared_with_key: str, role: str = "viewer") -> bool:
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO collection_shares (collection_id, shared_with_key, role) VALUES (?,?,?)",
            (collection_id, shared_with_key, role),
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def can_access(collection_id: str, api_key: str) -> tuple[bool, str]:
    """Return (can_access, role) for a given api_key on a collection."""
    coll = get_collection(collection_id)
    if not coll:
        return False, ""
    if coll.owner_key == api_key:
        return True, "owner"
    if coll.is_public:
        return True, "public"
    conn = _connect()
    row = conn.execute(
        "SELECT role FROM collection_shares WHERE collection_id=? AND shared_with_key=?",
        (collection_id, api_key),
    ).fetchone()
    conn.close()
    if row:
        return True, row["role"]
    return False, ""


def export_collection(collection_id: str, fmt: str) -> dict[str, Any]:
    """Export collection to CSV/SDF/Parquet-like structure."""
    items = get_collection_items(collection_id)
    coll = get_collection(collection_id)
    if fmt == "csv":
        import csv
        import io
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["smiles", "name", "notes", "properties"])
        for item in items:
            writer.writerow([
                item.smiles, item.name or "", item.notes or "",
                json.dumps(item.properties) if item.properties else "",
            ])
        return {"format": "csv", "filename": f"{coll.name}.csv", "content": buf.getvalue()}
    elif fmt == "sdf":
        from rdkit import Chem
        buf = io.StringIO()
        for item in items:
            mol = Chem.MolFromSmiles(item.smiles)
            if mol:
                if item.name:
                    mol.SetProp("_Name", item.name)
                if item.notes:
                    mol.SetProp("Notes", item.notes)
                if item.properties:
                    for k, v in item.properties.items():
                        mol.SetProp(str(k), str(v))
                buf.write(Chem.MolToMolBlock(mol))
                buf.write("$$\n\n")
        return {"format": "sdf", "filename": f"{coll.name}.sdf", "content": buf.getvalue()}
    elif fmt == "parquet":
        import pandas as pd
        import io
        rows = []
        for item in items:
            row = {"smiles": item.smiles, "name": item.name or "", "notes": item.notes or ""}
            if item.properties:
                row.update(item.properties)
            rows.append(row)
        df = pd.DataFrame(rows)
        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        return {"format": "parquet", "filename": f"{coll.name}.parquet", "content": buf.getvalue().decode("latin-1")}
    else:
        raise ValueError(f"Unknown export format: {fmt}")
