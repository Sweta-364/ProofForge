"""Hidden edge-case tests — validate the memory-leak fix thoroughly."""
import asyncio
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


async def test_memory_stable_under_load():
    """5000 unique tokens must not cause cache to exceed 1200 entries."""
    from starter.auth import verify_token, get_cache_size
    for i in range(5000):
        token = _make_token(f"load_user_{i}")
        await verify_token(token)
    size = get_cache_size()
    assert size <= 1200, (
        f"Cache grew to {size} entries — TTLCache(maxsize=1000) should cap at 1000"
    )


async def test_concurrent_access_safe():
    """50 concurrent verify_token calls must complete without exceptions."""
    from starter.auth import verify_token
    tokens = [_make_token(f"concurrent_{i}") for i in range(50)]
    results = await asyncio.gather(*[verify_token(t) for t in tokens], return_exceptions=True)
    errors = [r for r in results if isinstance(r, Exception)]
    assert len(errors) == 0, f"Got {len(errors)} exceptions under concurrent load: {errors}"


def test_uses_ttl_cache():
    """The fixed implementation must use cachetools.TTLCache, not a plain dict."""
    import cachetools
    from starter import auth
    assert isinstance(auth._token_cache, cachetools.TTLCache), (
        f"_token_cache is {type(auth._token_cache).__name__}, expected TTLCache. "
        "Fix: _token_cache = cachetools.TTLCache(maxsize=1000, ttl=300)"
    )


async def test_correct_token_still_works_after_evictions():
    """After filling the cache past maxsize, fresh valid tokens must still verify."""
    from starter.auth import verify_token
    # Fill the cache
    for i in range(1500):
        await verify_token(_make_token(f"fill_{i}"))
    # A new valid token must still work
    fresh = _make_token("fresh_user_after_evictions")
    result = await verify_token(fresh)
    assert result is not None
    assert result["sub"] == "fresh_user_after_evictions"
