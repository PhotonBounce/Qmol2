"""Async Redis client for caching, rate limits, and pub/sub."""
from __future__ import annotations
import json
import time
from typing import Any

import redis.asyncio as redis

import config

_redis_pool: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Return (or lazily create) the async Redis client."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.from_url(config.REDIS_URL, decode_responses=True)
    return _redis_pool


async def cache_get(key: str) -> Any | None:
    """Fetch a JSON-serialized value from Redis by key."""
    r = get_redis()
    val = await r.get(key)
    return json.loads(val) if val else None


async def cache_set(key: str, value: Any, ttl_seconds: int = 86400) -> None:
    """Store a JSON-serialized value in Redis with TTL."""
    r = get_redis()
    await r.setex(key, ttl_seconds, json.dumps(value))


async def cache_delete(key: str) -> None:
    """Remove a key from Redis."""
    r = get_redis()
    await r.delete(key)


async def rate_limit_check(key: str, max_requests: int, window_seconds: int) -> bool:
    """Sliding window rate limit using Redis sorted sets.

    Returns True if the request is allowed, False if it should be rejected.
    """
    r = get_redis()
    now = time.time()
    window_start = now - window_seconds
    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zcard(key)
    pipe.zadd(key, {str(now): now})
    pipe.expire(key, window_seconds)
    _, current_count, _, _ = await pipe.execute()
    return current_count < max_requests


async def rate_limit_reset(key: str | None = None) -> None:
    """Reset rate-limit state for a specific key or all keys."""
    r = get_redis()
    if key is None:
        # WARNING: this flushes the entire Redis DB — use only in dev/tests
        await r.flushdb()
    else:
        await r.delete(key)
