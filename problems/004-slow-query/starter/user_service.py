# user_service.py — User search with performance and security issues
import logging
import sqlite3
import time

logger = logging.getLogger(__name__)
DB_PATH = "/tmp/test_users.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def search_users(search_term: str) -> list:
    """Search users by username prefix. Currently slow and unsafe."""
    if not search_term:
        return []

    conn = get_db()
    cursor = conn.cursor()

    # BUG 1: String formatting — SQL injection vulnerability
    #        f-string means the query is re-parsed every call (no plan caching)
    # BUG 2: No index on username — every query is a full O(n) table scan
    # BUG 3: LIKE '%term%' with leading wildcard cannot use a B-tree index even after fix
    query = f"SELECT id, username, email, created_at FROM users WHERE username LIKE '%{search_term}%'"

    start = time.perf_counter()
    cursor.execute(query)
    rows = cursor.fetchall()
    elapsed = time.perf_counter() - start

    logger.info("Query took %.3fs, returned %d users", elapsed, len(rows))
    conn.close()
    return [dict(r) for r in rows]


def seed_database() -> None:
    """Creates and seeds the test database with 10,000 users."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY,
            username   TEXT    NOT NULL,
            email      TEXT    NOT NULL,
            created_at TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # NOTE: Intentionally NO index on username — that is part of the bug.
    conn.executemany(
        "INSERT OR IGNORE INTO users (id, username, email) VALUES (?, ?, ?)",
        [(i, f"user_{i:05d}", f"user_{i:05d}@example.com") for i in range(1, 10_001)],
    )
    # Realistic names mixed in for search tests
    conn.executemany(
        "INSERT OR IGNORE INTO users (id, username, email) VALUES (?, ?, ?)",
        [
            (10001, "alice_smith", "alice@example.com"),
            (10002, "alice_jones", "alicejones@example.com"),
            (10003, "bob_alice",   "bobalice@example.com"),
        ],
    )
    conn.commit()
    conn.close()
