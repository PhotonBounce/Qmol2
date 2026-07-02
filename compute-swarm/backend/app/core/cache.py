from __future__ import annotations

import json
import redis.asyncio as redis
from typing import Any

from app.config import settings

_redis_pool: redis.Redis | None = None


async def _get_redis() -> redis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_pool


async def get_cache(key: str) -> str | None:
    """Get a cached value by key. Returns None if not found or Redis is unavailable."""
    try:
        r = await _get_redis()
        value = await r.get(key)
        return value if value is not None else None
    except Exception:
        return None


async def set_cache(key: str, value: str | dict | Any, ttl: int = 60) -> None:
    """Set a cached value with an optional TTL (seconds)."""
    try:
        r = await _get_redis()
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        elif not isinstance(value, str):
            value = str(value)
        await r.setex(key, ttl, value)
    except Exception:
        pass


async def delete_cache(key: str) -> None:
    """Delete a cached key."""
    try:
        r = await _get_redis()
        await r.delete(key)
    except Exception:
        pass
