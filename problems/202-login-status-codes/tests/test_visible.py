"""Visible tests - status codes the frontend relies on."""
from fastapi.testclient import TestClient
from starter.main import app

client = TestClient(app)


def test_successful_login_returns_token():
    response = client.post(
        "/api/login", json={"username": "alice", "password": "Wonderland!42"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body.get("access_token") and body.get("token_type") == "bearer"


def test_wrong_password_returns_401():
    response = client.post(
        "/api/login", json={"username": "alice", "password": "wrong"}
    )
    assert response.status_code == 401


def test_missing_password_returns_422():
    response = client.post("/api/login", json={"username": "alice"})
    assert response.status_code == 422
