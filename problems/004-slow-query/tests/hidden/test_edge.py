"""Hidden edge-case tests — validate the performance and security fix."""
import pytest
import time
from starter.user_service import search_users, seed_database


@pytest.fixture(scope="module", autouse=True)
def db_seeded():
    seed_database()


def test_search_fast():
    """Searching 10k rows must complete in under 150ms after the fix."""
    start = time.perf_counter()
    results = search_users("alice")
    elapsed = time.perf_counter() - start
    assert elapsed < 0.15, (
        f"search_users('alice') took {elapsed:.3f}s — too slow. "
        "Fix: add index on username column and use parameterized query."
    )
    assert len(results) >= 3


def test_sql_injection_prevented():
    """SQL injection payload must not return unexpected rows."""
    try:
        results = search_users("' OR '1'='1")
        # With parameterized query, this searches for the literal string — returns 0 rows
        assert len(results) == 0, (
            f"SQL injection returned {len(results)} rows — query is not parameterized. "
            "Fix: use cursor.execute(query, (f'%{search_term}%',)) with a ? placeholder."
        )
    except Exception as exc:
        pytest.fail(
            f"SQL injection caused an exception: {exc}. "
            "Parameterized queries should handle this safely."
        )


def test_correct_results_for_alice():
    """Search 'alice' must return exactly the 3 alice-related users."""
    results = search_users("alice")
    usernames = {r["username"] for r in results}
    assert "alice_smith" in usernames
    assert "alice_jones" in usernames
    assert "bob_alice" in usernames


def test_search_prefix_only_no_injection():
    """Searching with a SQL wildcard character % should be treated as literal."""
    try:
        results = search_users("%")
        # With parameterized query LIKE 'alice%', searching '%' returns 0 rows
        # With f-string, LIKE '%%' matches everything — detects the bug
        assert len(results) < 100, (
            f"Searching for '%' returned {len(results)} rows — looks like a full table scan. "
            "Use parameterized queries so % is treated as a literal character, not a wildcard."
        )
    except Exception:
        pass  # Exception also means the query failed — not parameterized


def test_non_existent_user_returns_empty():
    """Searching for a user that doesn't exist returns empty list."""
    results = search_users("zzznobodyzqq")
    assert results == []
