"""One-time migration: hash all existing plaintext API keys."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.keys import _connect, _hash_key


def migrate():
    conn = _connect()
    cursor = conn.execute("SELECT key, email, tier, monthly_quota, active, created_at, stripe_customer_id FROM api_keys")
    rows = cursor.fetchall()
    migrated = 0
    for row in rows:
        key = row[0]
        # Check if already hashed
        existing = conn.execute("SELECT key_hash FROM api_keys WHERE key=?", (key,)).fetchone()
        if existing and existing[0] is not None:
            continue
        key_hash = _hash_key(key)
        conn.execute("UPDATE api_keys SET key_hash = ? WHERE key = ?", (key_hash, key))
        migrated += 1
    conn.commit()
    conn.close()
    print(f"Migrated {migrated} of {len(rows)} keys")


if __name__ == "__main__":
    migrate()
