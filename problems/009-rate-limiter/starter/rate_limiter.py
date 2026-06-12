# BROKEN: one shared list for every client, and old requests are never pruned.
import time


class RateLimiter:
    """Sliding-window limiter: max_requests per window_seconds, per client."""

    def __init__(self, max_requests: int = 5, window_seconds: int = 60, clock=time.monotonic):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clock = clock
        self._timestamps: list[float] = []

    def allow(self, client_id: str) -> bool:
        now = self.clock()
        if len(self._timestamps) >= self.max_requests:
            return False
        self._timestamps.append(now)
        return True
