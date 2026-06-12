"""Hidden edge cases."""
import time

import jwt
import pytest
from starter.auth_service import SECRET_KEY, verify_token


def test_wrong_algorithm_rejected():
    token = jwt.encode(
        {"sub": "admin", "exp": int(time.time()) + 3600},
        SECRET_KEY,
        algorithm="HS512",
    )
    with pytest.raises(jwt.PyJWTError):
        verify_token(token)


def test_garbage_token_rejected():
    with pytest.raises(jwt.PyJWTError):
        verify_token("definitely-not-a-jwt")
