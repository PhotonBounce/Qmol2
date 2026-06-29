from __future__ import annotations
import json
import time
from typing import Any

import redis.asyncio as redis
import redis as redis_sync

import config

_redis_pool: redis.Redis | None = None
_redis_pool_sync: redis_sync.Redis | None = None


def get_redis() -> redis.Redis:
    """Return (or lazily create) the async Redis client."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.from_url(config.REDIS_URL, decode_responses=True)
    return _redis_pool


def get_redis_sync() -> redis_sync.Redis:
    """Return (or lazily create) the sync Redis client (for Celery tasks)."""
    global _redis_pool_sync
    if _redis_pool_sync is None:
        _redis_pool_sync = redis_sync.from_url(config.REDIS_URL, decode_responses=True)
    return _redis_pool_sync


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


def publish_progress_sync(job_id: str, processed: int, total: int, status: str) -> None:
    """Publish a progress update to the Redis pub/sub channel for a job.

    Safe to call from synchronous Celery tasks.
    """
    try:
        r = get_redis_sync()
        channel = f"job:{job_id}:progress"
        r.publish(channel, json.dumps({
            "processed": processed,
            "total": total,
            "status": status,
        }))
    except Exception:
        pass


def store_progress_sync(job_id: str, processed: int, total: int, status: str,
                         ttl: int = 86400) -> None:
    """Store the latest progress snapshot in Redis (for polling / SSE init).

    Safe to call from synchronous Celery tasks.
    """
    try:
        r = get_redis_sync()
        key = f"job:{job_id}:progress:last"
        r.setex(key, ttl, json.dumps({
            "processed": processed,
            "total": total,
            "status": status,
        }))
    except Exception:
        pass


async def publish_progress(job_id: str, processed: int, total: int, status: str) -> None:
    """Async version of publish_progress_sync."""
    try:
        r = get_redis()
        channel = f"job:{job_id}:progress"
        await r.publish(channel, json.dumps({
            "processed": processed,
            "total": total,
            "status": status,
        }))
    except Exception:
        pass


async def store_progress(job_id: str, processed: int, total: int, status: str,
                         ttl: int = 86400) -> None:
    """Async version of store_progress_sync."""
    try:
        r = get_redis()
        key = f"job:{job_id}:progress:last"
        await r.setex(key, ttl, json.dumps({
            "processed": processed,
            "total": total,
            "status": status,
        }))
    except Exception:
        pass


async def get_progress(job_id: str) -> dict | None:
    """Read the latest progress snapshot for a job from Redis."""
    try:
        r = get_redis()
        data = await r.get(f"job:{job_id}:progress:last")
        return json.loads(data) if data else None
    except Exception:
        return None


def get_progress_sync(job_id: str) -> dict | None:
    """Sync version of get_progress."""
    try:
        r = get_redis_sync()
        data = r.get(f"job:{job_id}:progress:last")
        return json.loads(data) if data else None
    except Exception:
        return None
