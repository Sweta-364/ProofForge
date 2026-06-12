"""Visible tests - demonstrate both reported bugs."""
from starter.rate_limiter import RateLimiter


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def test_allows_up_to_limit_then_blocks():
    limiter = RateLimiter(max_requests=5, window_seconds=60, clock=FakeClock())
    results = [limiter.allow("alice") for _ in range(6)]
    assert results == [True, True, True, True, True, False]


def test_clients_are_independent():
    limiter = RateLimiter(max_requests=5, window_seconds=60, clock=FakeClock())
    for _ in range(5):
        limiter.allow("noisy-client")
    assert limiter.allow("quiet-client") is True, "one client exhausted everyone's budget"


def test_window_slides_after_expiry():
    clock = FakeClock()
    limiter = RateLimiter(max_requests=5, window_seconds=60, clock=clock)
    for _ in range(5):
        limiter.allow("alice")
    clock.advance(61)
    assert limiter.allow("alice") is True, "requests outside the window must not count"
