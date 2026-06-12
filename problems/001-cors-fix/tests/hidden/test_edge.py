"""Hidden edge-case tests — not shown in the workspace file tree."""
from fastapi.testclient import TestClient
from starter.main import app

client = TestClient(app)


def test_cors_not_wildcard():
    """Should use specific origin, not wildcard '*'."""
    response = client.get(
        "/api/users",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    origin_header = response.headers.get("access-control-allow-origin", "")
    assert origin_header != "*", "Must not use wildcard origin — configure specific origin"


def test_cors_allows_credentials():
    """Response must include Access-Control-Allow-Credentials: true."""
    response = client.get(
        "/api/users",
        headers={"Origin": "http://localhost:3000"},
    )
    creds = response.headers.get("access-control-allow-credentials", "")
    assert creds.lower() == "true", "allow_credentials=True must be set in CORSMiddleware"


def test_preflight_options_returns_200():
    """OPTIONS preflight on /api/login should succeed with CORS headers."""
    response = client.options(
        "/api/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


def test_cors_rejects_unknown_origin():
    """An unlisted origin should NOT receive the CORS allow-origin header."""
    response = client.get(
        "/api/users",
        headers={"Origin": "http://evil.com"},
    )
    origin_header = response.headers.get("access-control-allow-origin", "")
    assert origin_header != "http://evil.com", "Unlisted origins must be rejected"
