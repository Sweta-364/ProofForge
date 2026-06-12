"""Hidden edge cases."""
from fastapi.testclient import TestClient
from starter.main import app

client = TestClient(app)


def test_second_user_contract():
    data = client.get("/api/profile/2").json()
    assert data == {
        "id": 2,
        "username": "bob",
        "email": "bob@example.com",
        "joined": "2025-07-02",
    }


def test_404_has_json_detail():
    response = client.get("/api/profile/999")
    assert response.headers["content-type"].startswith("application/json")
    assert "detail" in response.json()
