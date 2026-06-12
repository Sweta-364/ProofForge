"""Visible tests — students can see these. They demonstrate the CORS bug."""
from fastapi.testclient import TestClient
from starter.main import app

client = TestClient(app)


def test_cors_headers_present():
    """OPTIONS /api/users with Origin header should return CORS allow header."""
    response = client.options(
        "/api/users",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


def test_get_users_with_cors():
    """GET /api/users with Origin header should return CORS header in response."""
    response = client.get(
        "/api/users",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
