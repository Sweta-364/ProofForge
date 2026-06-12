"""Visible tests — demonstrate the unbounded cache memory leak."""
import pytest
from datetime import datetime, timezone, timedelta

import jwt

SECRET_KEY = "dev-secret-key-not-for-production"


def _make_token(subject: str) -> str:
    return jwt.encode(
        {"sub": subject, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        SECRET_KEY,
        algorithm="HS256",
    )


@pytest.fixture(autouse=True)
def reset_cache():
    from starter.auth import clear_cache
    clear_cache()
    yield
    clear_cache()


async def test_valid_token_returns_payload():
    """A valid token should return the decoded payload."""
    from starter.auth import verify_token
    token = _make_token("user_happy_path")
    payload = await verify_token(token)
    assert payload is not None
    assert payload["sub"] == "user_happy_path"


async def test_cache_has_size_limit():
    """Cache must not grow unboundedly — add 2000 tokens, size must stay < 1500.
    Currently FAILS with broken code (plain dict grows to 2000)."""
    from starter.auth import verify_token, get_cache_size
    for i in range(2000):
        token = _make_token(f"user_{i}")
        await verify_token(token)
    size = get_cache_size()
    assert size < 1500, (
        f"Cache has {size} entries — it's growing unboundedly. "
        "Fix: replace plain dict with cachetools.TTLCache(maxsize=1000, ttl=300)"
    )


async def test_expired_token_returns_none():
    """An expired JWT should return None and must NOT be cached."""
    from starter.auth import verify_token, get_cache_size
    expired = jwt.encode(
        {"sub": "expireduser", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
        SECRET_KEY,
        algorithm="HS256",
    )
    result = await verify_token(expired)
    assert result is None
    assert get_cache_size() == 0, "Expired tokens must not be added to the cache"
