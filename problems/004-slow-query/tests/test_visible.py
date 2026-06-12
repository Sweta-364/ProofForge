"""Visible tests — show what the endpoint must do correctly."""
import pytest
from starter.user_service import search_users, seed_database


@pytest.fixture(scope="module", autouse=True)
def db_seeded():
    seed_database()


def test_search_returns_results():
    """Search 'alice' should return at least 3 matching users."""
    results = search_users("alice")
    assert len(results) >= 3, f"Expected ≥3 results for 'alice', got {len(results)}"


def test_search_returns_correct_fields():
    """Each result must have id, username, email, created_at fields."""
    results = search_users("alice")
    assert len(results) > 0
    row = results[0]
    for field in ("id", "username", "email", "created_at"):
        assert field in row, f"Missing field: {field}"


def test_empty_search_returns_empty():
    """Empty search string should return empty list, not all users."""
    results = search_users("")
    assert results == [], f"Expected [] for empty search, got {len(results)} rows"
