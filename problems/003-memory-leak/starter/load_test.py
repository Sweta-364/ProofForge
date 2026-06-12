"""
Load test to reproduce the memory leak.
Run: python load_test.py
Watch memory grow with each batch of requests.
"""
import tracemalloc
import asyncio
from datetime import datetime, timezone, timedelta

import jwt

SECRET_KEY = "dev-secret-key-not-for-production"


def make_token(subject: str) -> str:
    return jwt.encode(
        {"sub": subject, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        SECRET_KEY,
        algorithm="HS256",
    )


async def main():
    from starter.auth import verify_token, get_cache_size

    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    print("Generating and verifying 10,000 unique tokens...")
    for i in range(10_000):
        token = make_token(f"user_{i}")
        await verify_token(token)

    snapshot_after = tracemalloc.take_snapshot()
    stats = snapshot_after.compare_to(snapshot_before, "lineno")

    print(f"\nCache size after 10,000 tokens: {get_cache_size()}")
    print("\nTop memory allocations:")
    for stat in stats[:5]:
        print(f"  {stat}")

    total_added = sum(s.size_diff for s in stats if s.size_diff > 0)
    print(f"\nTotal memory added: {total_added / 1024:.1f} KB")
    print("\nWith the bug:  cache = 10,000 entries (never evicted)")
    print("With the fix:  cache = ≤1,000 entries (TTLCache with maxsize)")


if __name__ == "__main__":
    asyncio.run(main())
