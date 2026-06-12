"""Visible tests - the audit findings."""
import pytest
from fastapi.testclient import TestClient
from starter.main import REFRESH_TOKENS, app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_tokens():
    REFRESH_TOKENS.clear()
    yield
    REFRESH_TOKENS.clear()


def _login():
    response = client.post(
        "/api/auth/login", json={"username": "alice", "password": "Wonderland!42"}
    )
    assert response.status_code == 200
    return response.json()


def test_refresh_with_valid_token_works():
    tokens = _login()
    response = client.post(
        "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 200
    assert response.json().get("access_token")


def test_unknown_refresh_token_rejected():
    _login()
    response = client.post("/api/auth/refresh", json={"refresh_token": "stolen-or-bogus"})
    assert response.status_code == 401


def test_refresh_rotates_the_token():
    tokens = _login()
    first = client.post(
        "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    ).json()
    assert first["refresh_token"] != tokens["refresh_token"], "token was not rotated"
    replay = client.post(
        "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert replay.status_code == 401, "the old refresh token must stop working"
