"""Auth and user profile endpoint tests."""
import secrets
from datetime import datetime, timedelta, timezone

import asyncpg
import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.config import settings


# ── JWT helper ────────────────────────────────────────────────────────────────

def _make_jwt(user_id: str, github_login: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "github_login": github_login,
        "jti": secrets.token_hex(16),
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_github_redirect(client: TestClient):
    """GET /auth/github returns 302 redirecting to github.com OAuth page."""
    response = client.get("/api/v1/auth/github", follow_redirects=False)
    assert response.status_code == 302
    location = response.headers["location"]
    assert "github.com/login/oauth/authorize" in location
    assert "client_id=" in location


def test_callback_bad_state(client: TestClient):
    """Callback with an unknown state must return 400."""
    response = client.get(
        "/api/v1/auth/callback",
        params={"code": "fake_code", "state": "totally_invalid_state_xyz"},
    )
    assert response.status_code == 400
    assert "state" in response.json()["detail"].lower()


def test_get_me_no_token(client: TestClient):
    """GET /users/me without a token returns 401."""
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


async def test_get_me_valid_token(client: TestClient, db_conn: asyncpg.Connection):
    """GET /users/me with a valid JWT returns the user profile."""
    user = await db_conn.fetchrow(
        """
        INSERT INTO users (github_id, github_login, name, email)
        VALUES ($1, $2, $3, $4)
        RETURNING id, github_login
        """,
        "gh_auth_test_001",
        "auth_test_user",
        "Auth Test User",
        "authtest@example.com",
    )
    token = _make_jwt(str(user["id"]), user["github_login"])

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["github_login"] == "auth_test_user"
    assert data["email"] == "authtest@example.com"


async def test_update_track(client: TestClient, db_conn: asyncpg.Connection):
    """PUT /users/me/track with a valid track updates career_track and resets difficulty."""
    user = await db_conn.fetchrow(
        """
        INSERT INTO users (github_id, github_login, name, career_track, current_difficulty)
        VALUES ($1, $2, $3, 'fullstack', 'mid')
        RETURNING id, github_login
        """,
        "gh_auth_test_002",
        "track_test_user",
        "Track Test User",
    )
    token = _make_jwt(str(user["id"]), user["github_login"])

    response = client.put(
        "/api/v1/users/me/track",
        json={"track": "backend"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["career_track"] == "backend"
    assert data["current_difficulty"] == "junior"


async def test_update_track_invalid(client: TestClient, db_conn: asyncpg.Connection):
    """PUT /users/me/track with an invalid track returns 400."""
    user = await db_conn.fetchrow(
        """
        INSERT INTO users (github_id, github_login, name)
        VALUES ($1, $2, $3)
        RETURNING id, github_login
        """,
        "gh_auth_test_003",
        "invalid_track_user",
        "Invalid Track User",
    )
    token = _make_jwt(str(user["id"]), user["github_login"])

    response = client.put(
        "/api/v1/users/me/track",
        json={"track": "quantum_computing"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


async def test_logout_invalidates_token(client: TestClient, db_conn: asyncpg.Connection):
    """After logout, the same JWT is rejected with 401."""
    user = await db_conn.fetchrow(
        """
        INSERT INTO users (github_id, github_login, name)
        VALUES ($1, $2, $3)
        RETURNING id, github_login
        """,
        "gh_auth_test_004",
        "logout_test_user",
        "Logout Test User",
    )
    token = _make_jwt(str(user["id"]), user["github_login"])
    auth_headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/v1/users/me", headers=auth_headers).status_code == 200

    logout_resp = client.post("/api/v1/auth/logout", headers=auth_headers)
    assert logout_resp.status_code == 200
    assert logout_resp.json() == {"message": "logged out"}

    assert client.get("/api/v1/users/me", headers=auth_headers).status_code == 401


async def test_refresh_returns_new_token(client: TestClient, db_conn: asyncpg.Connection):
    """POST /auth/refresh returns a new token that is valid."""
    user = await db_conn.fetchrow(
        """
        INSERT INTO users (github_id, github_login, name)
        VALUES ($1, $2, $3)
        RETURNING id, github_login
        """,
        "gh_auth_test_005",
        "refresh_test_user",
        "Refresh Test User",
    )
    old_token = _make_jwt(str(user["id"]), user["github_login"])

    resp = client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {old_token}"},
    )
    assert resp.status_code == 200
    new_token = resp.json()["access_token"]
    assert new_token != old_token

    me_resp = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert me_resp.status_code == 200
