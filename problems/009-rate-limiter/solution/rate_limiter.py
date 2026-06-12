import time
from collections import defaultdict, deque


class RateLimiter:
    """Sliding-window limiter: max_requests per window_seconds, per client."""

    def __init__(self, max_requests: int = 5, window_seconds: int = 60, clock=time.monotonic):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clock = clock
        self._timestamps: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, client_id: str) -> bool:
        now = self.clock()
        window = self._timestamps[client_id]
        cutoff = now - self.window_seconds
        while window and window[0] <= cutoff:
            window.popleft()
        if len(window) >= self.max_requests:
            return False
        window.append(now)
        return True
