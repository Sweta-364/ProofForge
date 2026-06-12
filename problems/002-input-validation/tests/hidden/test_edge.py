"""Hidden edge-case tests — not shown to students."""
import pytest
from fastapi.testclient import TestClient
from starter.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_login_with_unicode_cafe():
    """carol + 'café' must return 200 (correct password, non-ASCII)."""
    response = client.post("/api/auth/login", json={"username": "carol", "password": "café"})
    assert response.status_code == 200, f"Expected 200 for correct non-ASCII password, got {response.status_code}"
    assert "access_token" in response.json()


def test_login_wrong_unicode_password_returns_401():
    """Wrong non-ASCII password must return 401, not 500."""
    response = client.post("/api/auth/login", json={"username": "carol", "password": "cafè"})
    assert response.status_code == 401


def test_login_with_emoji_returns_401_not_500():
    """Emoji in password must return 401 (wrong creds), never 500."""
    response = client.post("/api/auth/login", json={"username": "alice", "password": "pass\U0001f511word"})
    assert response.status_code != 500, "UnicodeEncodeError must not produce 500"
    assert response.status_code == 401


def test_wrong_password_returns_401():
    """alice + 'wrongpassword' must return 401, not 500."""
    response = client.post("/api/auth/login", json={"username": "alice", "password": "wrongpassword"})
    assert response.status_code == 401


def test_correct_special_password_bob():
    """bob + 'secur3#pass' (special ASCII chars) must return 200."""
    response = client.post("/api/auth/login", json={"username": "bob", "password": "secur3#pass"})
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.parametrize("password", [
    "pàss",    # à
    "péss",    # é
    "püss",    # ü
    "pñss",    # ñ
    "\U0001f525",   # 🔥
    "\U0001f511",   # 🔑
    "p中ss",    # 中
    "pаss",    # а (Cyrillic)
    "café",    # café
    "αβ", # αβ
])
def test_no_500_for_non_ascii_passwords(password):
    """Any non-ASCII password must not produce a 500 response."""
    response = client.post("/api/auth/login", json={"username": "alice", "password": password})
    assert response.status_code != 500, f"Got 500 for password containing non-ASCII chars: {password!r}"
