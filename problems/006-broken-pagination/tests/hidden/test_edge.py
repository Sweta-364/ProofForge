"""Hidden edge cases."""
from fastapi.testclient import TestClient
from starter.main import app

client = TestClient(app)


def test_page_beyond_range_returns_empty():
    data = client.get("/api/items", params={"page": 99, "page_size": 10}).json()
    assert data["items"] == []


def test_odd_page_size():
    data = client.get("/api/items", params={"page": 4, "page_size": 7}).json()
    ids = [i["id"] for i in data["items"]]
    assert ids == [22, 23, 24, 25]
    assert data["total_pages"] == 4
