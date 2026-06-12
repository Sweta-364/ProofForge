"""Hidden edge cases."""
import pytest
from fastapi.testclient import TestClient

import starter.main as main_module
from starter.main import REFRESH_TOKENS, app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_tokens():
    REFRESH_TOKENS.clear()
    yield
    REFRESH_TOKENS.clear()


def _login():
    return client.post(
        "/api/auth/login", json={"username": "alice", "password": "Wonderland!42"}
    ).json()


def test_expired_refresh_token_rejected(monkeypatch):
    tokens = _login()
    monkeypatch.setattr(main_module, "REFRESH_TTL", -1)
    response = client.post(
        "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 401


def test_rotated_token_chain_works():
    tokens = _login()
    current = tokens["refresh_token"]
    for _ in range(3):
        response = client.post("/api/auth/refresh", json={"refresh_token": current})
        assert response.status_code == 200
        current = response.json()["refresh_token"]
