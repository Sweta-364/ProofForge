"""Hidden edge cases."""
import pytest
from starter.product_repo import search_products, seed_database


@pytest.fixture(autouse=True)
def seeded():
    seed_database()


def test_or_true_injection_returns_nothing():
    results = search_products("%' OR '1'='1")
    assert results == []


def test_stacked_query_attempt_is_safe():
    search_products("'; DROP TABLE products; --")
    assert len(search_products("Laptop")) == 2
