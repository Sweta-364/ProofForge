"""Visible tests - normal use plus the two reported failures."""
import pytest
from starter.product_repo import search_products, seed_database


@pytest.fixture(autouse=True)
def seeded():
    seed_database()


def test_normal_search_works():
    results = search_products("Laptop")
    assert len(results) == 2


def test_apostrophe_search_does_not_crash():
    results = search_products("O'Briens")
    assert len(results) == 1
    assert results[0]["name"] == "O'Briens Hot Sauce"


def test_union_injection_blocked():
    payload = "' UNION SELECT id, username, password FROM users --"
    results = search_products(payload)
    leaked = [r for r in results if "TopSecretHunter2" in str(list(r.values()))]
    assert leaked == [], "Injection leaked user passwords!"
