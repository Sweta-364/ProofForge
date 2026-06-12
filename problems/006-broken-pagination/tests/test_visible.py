"""Visible tests - demonstrate the pagination bug."""
from fastapi.testclient import TestClient
from starter.main import app

client = TestClient(app)


def test_first_page_starts_at_first_item():
    data = client.get("/api/items", params={"page": 1, "page_size": 10}).json()
    ids = [i["id"] for i in data["items"]]
    assert ids == list(range(1, 11)), f"page 1 should be items 1-10, got {ids}"


def test_last_page_has_remaining_items():
    data = client.get("/api/items", params={"page": 3, "page_size": 10}).json()
    ids = [i["id"] for i in data["items"]]
    assert ids == [21, 22, 23, 24, 25], f"page 3 should be items 21-25, got {ids}"


def test_total_pages_rounds_up():
    data = client.get("/api/items", params={"page": 1, "page_size": 10}).json()
    assert data["total_pages"] == 3, f"25 items / 10 per page = 3 pages, got {data['total_pages']}"
