"""Simple in-memory sliding-window rate limiter."""

from __future__ import annotations

import time
from collections import deque
from typing import Dict

# key -> deque of timestamps
_buckets: Dict[str, deque] = {}


def is_rate_limited(key: str, limit: int, window_seconds: int = 60) -> bool:
    """Return True if the key has exceeded the allowed number of requests in the window."""
    now = time.monotonic()
    window = deque()
    if key in _buckets:
        window = _buckets[key]
        # Evict stale entries
        while window and window[0] < now - window_seconds:
            window.popleft()
    window.append(now)
    _buckets[key] = window
    return len(window) > limit


def cleanup_buckets(max_age: int = 300) -> None:
    """Remove stale buckets to prevent unbounded memory growth."""
    now = time.monotonic()
    stale = [k for k, v in _buckets.items() if v and v[-1] < now - max_age]
    for k in stale:
        del _buckets[k]
