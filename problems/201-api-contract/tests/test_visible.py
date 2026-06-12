"""Visible tests - the documented contract."""
from fastapi.testclient import TestClient
from starter.main import app

client = TestClient(app)


def test_profile_uses_documented_keys():
    data = client.get("/api/profile/1").json()
    assert set(data.keys()) == {"id", "username", "email", "joined"}, (
        f"wrong keys: {sorted(data.keys())}"
    )


def test_id_is_an_integer():
    data = client.get("/api/profile/1").json()
    assert data["id"] == 1 and isinstance(data["id"], int)


def test_unknown_user_returns_404():
    response = client.get("/api/profile/999")
    assert response.status_code == 404
