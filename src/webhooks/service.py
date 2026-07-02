"""Enhanced webhook system with events, delivery logs, and HMAC signing.

Extends the legacy src/webhooks_out.py with per-webhook event filtering,
UUID-based IDs, delivery logs, and secret rotation.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import secrets
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

try:
    import requests  # type: ignore
except ImportError:
    requests = None

from src.webhooks_out import _is_valid_webhook_url

DEFAULT_DB = Path("data/webhooks_v2.sqlite")
MAX_ATTEMPTS = 5
BACKOFF_BASE = 2.0

_SCHEMA = """
CREATE TABLE IF NOT EXISTS webhooks_v2 (
    id TEXT PRIMARY KEY,
    api_key TEXT NOT NULL,
    url TEXT NOT NULL,
    events TEXT NOT NULL,
    secret TEXT NOT NULL,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_webhooks_v2_api_key ON webhooks_v2(api_key);

CREATE TABLE IF NOT EXISTS webhook_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    webhook_id TEXT NOT NULL,
    event TEXT NOT NULL,
    payload TEXT,
    attempts INTEGER DEFAULT 0,
    last_status INTEGER,
    last_error TEXT,
    delivered INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_webhook_id ON webhook_logs(webhook_id);
"""


@dataclass
class WebhookInfo:
    id: str
    api_key: str
    url: str
    events: str
    secret: str
    active: bool
    created_at: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["active"] = bool(d["active"])
        d["has_secret"] = bool(d["secret"])
        del d["secret"]
        return d


@dataclass
class WebhookLogInfo:
    id: int
    webhook_id: str
    event: str
    payload: str
    attempts: int
    last_status: int | None
    last_error: str | None
    delivered: bool
    created_at: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["delivered"] = bool(d["delivered"])
        try:
            d["payload"] = json.loads(d["payload"]) if d["payload"] else {}
        except json.JSONDecodeError:
            pass
        return d


def _connect() -> sqlite3.Connection:
    DEFAULT_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DEFAULT_DB))
    conn.executescript(_SCHEMA)
    conn.row_factory = sqlite3.Row
    return conn


def _generate_secret() -> str:
    return secrets.token_hex(32)


def create_webhook(api_key: str, url: str, events: str, secret: str | None = None) -> WebhookInfo:
    if not _is_valid_webhook_url(url):
        raise ValueError(f"Invalid or blocked webhook URL: {url}")
    conn = _connect()
    wid = str(uuid.uuid4())
    sec = secret or _generate_secret()
    conn.execute(
        "INSERT INTO webhooks_v2 (id, api_key, url, events, secret) VALUES (?,?,?,?,?)",
        (wid, api_key, url, events, sec),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM webhooks_v2 WHERE id=?", (wid,)).fetchone()
    conn.close()
    return WebhookInfo(
        id=row["id"], api_key=row["api_key"], url=row["url"],
        events=row["events"], secret=row["secret"],
        active=bool(row["active"]), created_at=row["created_at"],
    )


def list_webhooks(api_key: str) -> list[WebhookInfo]:
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM webhooks_v2 WHERE api_key=? ORDER BY created_at DESC",
        (api_key,),
    ).fetchall()
    conn.close()
    return [
        WebhookInfo(
            id=r["id"], api_key=r["api_key"], url=r["url"],
            events=r["events"], secret=r["secret"],
            active=bool(r["active"]), created_at=r["created_at"],
        )
        for r in rows
    ]


def get_webhook(webhook_id: str) -> WebhookInfo | None:
    conn = _connect()
    row = conn.execute("SELECT * FROM webhooks_v2 WHERE id=?", (webhook_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return WebhookInfo(
        id=row["id"], api_key=row["api_key"], url=row["url"],
        events=row["events"], secret=row["secret"],
        active=bool(row["active"]), created_at=row["created_at"],
    )


def delete_webhook(webhook_id: str) -> bool:
    conn = _connect()
    cur = conn.execute("DELETE FROM webhooks_v2 WHERE id=?", (webhook_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def rotate_secret(webhook_id: str) -> str | None:
    conn = _connect()
    new_secret = _generate_secret()
    cur = conn.execute(
        "UPDATE webhooks_v2 SET secret=? WHERE id=?",
        (new_secret, webhook_id),
    )
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        return None
    return new_secret


def get_logs(webhook_id: str, limit: int = 100) -> list[WebhookLogInfo]:
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM webhook_logs WHERE webhook_id=? ORDER BY created_at DESC LIMIT ?",
        (webhook_id, limit),
    ).fetchall()
    conn.close()
    return [
        WebhookLogInfo(
            id=r["id"], webhook_id=r["webhook_id"], event=r["event"],
            payload=r["payload"], attempts=r["attempts"], last_status=r["last_status"],
            last_error=r["last_error"], delivered=bool(r["delivered"]), created_at=r["created_at"],
        )
        for r in rows
    ]


def deliver(webhook_id: str, event: str, payload: dict[str, Any]) -> bool:
    """Attempt delivery. Returns True on success. Logs every attempt."""
    wh = get_webhook(webhook_id)
    if not wh or not wh.active or requests is None:
        return False
    # Re-validate URL at delivery time to prevent DNS rebinding / time-of-check-time-of-use
    if not _is_valid_webhook_url(wh.url):
        return False
    # Check event filter
    allowed_events = {e.strip() for e in wh.events.split(",")}
    if event not in allowed_events and "*" not in allowed_events:
        return False

    body = json.dumps({"event": event, **payload})
    headers = {"content-type": "application/json"}
    sig = hmac.new(wh.secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    headers["x-qmol-signature"] = f"sha256={sig}"

    last_status: int | None = None
    last_err: str | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            r = requests.post(wh.url, data=body, headers=headers, timeout=15)
            last_status = r.status_code
            if 200 <= r.status_code < 300:
                _log(webhook_id, event, body, attempt, last_status, None, True)
                return True
            last_err = f"non-2xx: {r.status_code} {r.text[:200]}"
        except Exception as e:
            last_err = str(e)[:500]
        if attempt < MAX_ATTEMPTS:
            time.sleep(BACKOFF_BASE ** attempt)
    _log(webhook_id, event, body, MAX_ATTEMPTS, last_status, last_err, False)
    return False


def deliver_async(webhook_id: str, event: str, payload: dict[str, Any]) -> None:
    """Fire-and-forget background delivery."""
    t = threading.Thread(target=deliver, args=(webhook_id, event, payload), daemon=True)
    t.start()


def _log(webhook_id: str, event: str, body: str, attempts: int,
         status: int | None, error: str | None, delivered: bool) -> None:
    conn = _connect()
    conn.execute(
        "INSERT INTO webhook_logs (webhook_id, event, payload, attempts, last_status, last_error, delivered) "
        "VALUES (?,?,?,?,?,?,?)",
        (webhook_id, event, body, attempts, status, error, 1 if delivered else 0),
    )
    conn.commit()
    conn.close()


def test_payload() -> dict[str, Any]:
    """Return a standard test payload for webhook verification."""
    return {
        "test": True,
        "timestamp": time.time(),
        "message": "This is a test webhook from Q-Mol",
    }
