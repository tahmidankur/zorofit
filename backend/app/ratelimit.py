"""Per-client request limits for an API that has no logins.

Device ids are free to mint, so they can't be the only key for abuse limits; the client IP is.
Limits live in memory: the free Render plan runs one instance, and a restart only resets the windows.
"""

import threading
import time
from collections import deque

from fastapi import HTTPException, Request

# Cloudflare sits in front of Render and rejects requests that try to set this header themselves,
# so it is trustworthy there. X-Forwarded-For is not: Render keeps whatever the client sent first.
TRUSTED_IP_HEADERS = ("cf-connecting-ip", "true-client-ip")


def client_ip(request: Request) -> str:
    for header in TRUSTED_IP_HEADERS:
        value = request.headers.get(header)
        if value:
            return value.strip()
    return request.client.host if request.client else "unknown"


class SlidingWindowLimiter:
    def __init__(self, name: str, limit: int, window_seconds: int):
        self.name = name
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            if len(self._hits) > 10_000:
                self._sweep(now)
            return True

    def _sweep(self, now: float) -> None:
        stale = [key for key, hits in self._hits.items() if not hits or hits[-1] <= now - self.window]
        for key in stale:
            del self._hits[key]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


ALL_REQUESTS = SlidingWindowLimiter("requests", limit=300, window_seconds=5 * 60)
NEW_DEVICES = SlidingWindowLimiter("new devices", limit=20, window_seconds=60 * 60)
CHAT = SlidingWindowLimiter("chat", limit=60, window_seconds=60 * 60)
DEMO = SlidingWindowLimiter("demo data", limit=5, window_seconds=60 * 60)

LIMITERS = (ALL_REQUESTS, NEW_DEVICES, CHAT, DEMO)


def enforce(limiter: SlidingWindowLimiter, request: Request, message: str) -> None:
    if not limiter.allow(client_ip(request)):
        raise HTTPException(status_code=429, detail=message)
