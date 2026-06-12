# auth.py — Authentication middleware with memory leak
import logging
from typing import Optional

import jwt

logger = logging.getLogger(__name__)

SECRET_KEY = "dev-secret-key-not-for-production"

# BUG: This dict grows forever. Every token ever seen is cached here.
# Tokens are added in verify_token() but nothing ever removes them.
_token_cache: dict = {}


async def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token and return payload. Caches results for performance."""
    if token in _token_cache:
        return _token_cache[token]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        # BUG: Caches indefinitely with no eviction policy
        _token_cache[token] = payload
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Expired token presented")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid token: %s", e)
        return None


def get_cache_size() -> int:
    """Returns current cache size for monitoring."""
    return len(_token_cache)


def clear_cache() -> None:
    """Clear the token cache (test helper)."""
    _token_cache.clear()
