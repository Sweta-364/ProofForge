"""
Test fixtures shared across the test suite.

Session-scoped fixtures (client, db_conn, redis_conn, minio_client) are created
once per pytest session and torn down at the end.

apply_migrations ensures 001_initial.sql is applied before any test.
truncate_tables cleans all data tables after each test to prevent cross-test
contamination.
"""
from pathlib import Path

import asyncpg
import aioredis
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from minio import Minio

from app.config import settings
from app.main import app

# ── HTTP client ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def client():
    """Sync ASGI test client. Entering the context triggers the FastAPI lifespan."""
    with TestClient(app) as c:
        yield c


# ── Direct service connections (for setup / assertions, not HTTP) ─────────────

@pytest_asyncio.fixture(scope="session")
async def db_conn() -> asyncpg.Connection:
    conn = await asyncpg.connect(settings.DATABASE_URL)
    yield conn
    await conn.close()


@pytest_asyncio.fixture(scope="session")
async def redis_conn() -> aioredis.Redis:
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    await r.ping()
    yield r
    await r.close()


@pytest.fixture(scope="session")
def minio_client() -> Minio:
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=False,
    )


# ── Migration guard ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session", autouse=True)
async def apply_migrations(db_conn: asyncpg.Connection) -> None:
    """Idempotently apply all SQL migrations before the test session begins."""
    await db_conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version    VARCHAR(255) PRIMARY KEY,
            applied_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """)
    applied = {
        row["version"]
        for row in await db_conn.fetch("SELECT version FROM schema_migrations")
    }
    sql_dir = Path(__file__).parent.parent / "migrations"
    for sql_file in sorted(sql_dir.glob("*.sql")):
        if sql_file.name not in applied:
            async with db_conn.transaction():
                await db_conn.execute(sql_file.read_text(encoding="utf-8"))
                await db_conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES ($1)",
                    sql_file.name,
                )


# ── Per-test teardown ─────────────────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def truncate_tables(db_conn: asyncpg.Connection) -> None:
    """Wipe all data tables after each test so tests don't affect each other."""
    yield
    # Truncate in reverse FK dependency order; RESTART IDENTITY resets sequences
    await db_conn.execute("""
        TRUNCATE TABLE
            reviews, submissions, active_sessions,
            portfolio_cards, test_cases, problems, users
        RESTART IDENTITY CASCADE
    """)
