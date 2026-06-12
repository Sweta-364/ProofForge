"""Visible tests — demonstrate the special-character login bug."""
from fastapi.testclient import TestClient
from starter.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_login_normal_password():
    """alice + 'password' (all ASCII) should return 200 with token."""
    response = client.post("/api/auth/login", json={"username": "alice", "password": "password"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_special_chars_not_500():
    """Login with a non-ASCII password must never return 500.
    Currently BROKEN — carol's password 'café' crashes with UnicodeEncodeError."""
    response = client.post("/api/auth/login", json={"username": "carol", "password": "café"})
    assert response.status_code != 500, (
        "Server returned 500 — UnicodeEncodeError from encode('ascii'). "
        "Fix: change encode('ascii') to encode('utf-8')"
    )
