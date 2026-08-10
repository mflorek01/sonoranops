"""Small single-process limiter for the public portfolio chat endpoint."""
from __future__ import annotations

import hashlib
import threading
import time
from collections import deque


class ChatLimiter:
    def __init__(self, per_hour: int = 8, max_concurrent: int = 2, daily_cap: int = 30) -> None:
        self.per_hour, self.max_concurrent, self.daily_cap = per_hour, max_concurrent, daily_cap
        self._lock, self._active, self._requests, self._daily = threading.Lock(), 0, {}, deque()

    def acquire(self, client: str) -> str | None:
        identifier = hashlib.sha256(client.encode()).hexdigest()[:32]
        now = time.monotonic()
        with self._lock:
            while self._daily and now - self._daily[0] >= 86400:
                self._daily.popleft()
            requests = self._requests.setdefault(identifier, deque())
            while requests and now - requests[0] >= 3600:
                requests.popleft()
            if (
                self._active >= self.max_concurrent
                or len(requests) >= self.per_hour
                or len(self._daily) >= self.daily_cap
            ):
                return None
            requests.append(now)
            self._daily.append(now)
            self._active += 1
        return identifier

    def release(self) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)
