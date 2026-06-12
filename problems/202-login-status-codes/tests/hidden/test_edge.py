"""Hidden edge cases."""
from fastapi.testclient import TestClient
from starter.main import app

client = TestClient(app)


def test_unknown_username_returns_401():
    response = client.post(
        "/api/login", json={"username": "mallory", "password": "whatever"}
    )
    assert response.status_code == 401


def test_401_does_not_reveal_which_field_was_wrong():
    response = client.post(
        "/api/login", json={"username": "alice", "password": "wrong"}
    )
    detail = str(response.json().get("detail", "")).lower()
    assert "password" not in detail or "username" in detail, (
        "the error must not reveal whether the username or password was wrong"
    )
