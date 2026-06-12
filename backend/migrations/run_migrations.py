#!/usr/bin/env python3
"""
Idempotent migration runner.

Usage:
    DATABASE_URL=postgresql://... python migrations/run_migrations.py

Tracks applied migrations in schema_migrations table.
Safe to run multiple times — already-applied files are skipped.
"""
import asyncio
import os
import sys
from pathlib import Path

import asyncpg

MIGRATIONS_DIR = Path(__file__).parent


async def run_all_migrations(database_url: str | None = None) -> None:
    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    conn = await asyncpg.connect(url)
    try:
        # Bootstrap tracking table (idempotent)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version    VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            )
        """)

        applied = {
            row["version"]
            for row in await conn.fetch("SELECT version FROM schema_migrations ORDER BY version")
        }

        sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        if not sql_files:
            print("No SQL migration files found.")
            return

        for sql_file in sql_files:
            version = sql_file.name
            if version in applied:
                print(f"  skip  {version}  (already applied)")
                continue

            print(f"  apply {version} ...", end=" ", flush=True)
            sql = sql_file.read_text(encoding="utf-8")

            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES ($1)", version
                )
            print("done")

        print("Migrations complete.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run_all_migrations())
