"""Visible tests - show the token verification holes."""
import time

import jwt
import pytest
from starter.auth_service import create_token, verify_token


def test_valid_token_round_trip():
    assert verify_token(create_token("alice")) == "alice"


def test_expired_token_rejected():
    token = create_token("alice", expires_in_seconds=-10)
    with pytest.raises(jwt.PyJWTError):
        verify_token(token)


def test_forged_signature_rejected():
    forged = jwt.encode(
        {"sub": "admin", "exp": int(time.time()) + 3600},
        "attacker-key",
        algorithm="HS256",
    )
    with pytest.raises(jwt.PyJWTError):
        verify_token(forged)
