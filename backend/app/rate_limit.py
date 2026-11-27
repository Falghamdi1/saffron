"""Per-user sliding window, to protect the model quota. In memory, per process."""

import time
from collections import defaultdict, deque
from threading import Lock


class RateLimiter:
    def __init__(self, per_minute: int) -> None:
        self._limit = per_minute
        self._calls: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            calls = self._calls[key]
            while calls and now - calls[0] > 60:
                calls.popleft()
            if len(calls) >= self._limit:
                return False
            calls.append(now)
            return True
