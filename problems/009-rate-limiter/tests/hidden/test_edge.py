"""Hidden edge cases."""
from starter.rate_limiter import RateLimiter


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def test_partial_window_slide():
    clock = FakeClock()
    limiter = RateLimiter(max_requests=5, window_seconds=60, clock=clock)
    for _ in range(3):
        limiter.allow("alice")
    clock.advance(30)
    assert limiter.allow("alice") is True
    assert limiter.allow("alice") is True
    assert limiter.allow("alice") is False
    clock.advance(31)
    assert limiter.allow("alice") is True


def test_zero_budget_always_blocks():
    limiter = RateLimiter(max_requests=0, window_seconds=60, clock=FakeClock())
    assert limiter.allow("alice") is False
