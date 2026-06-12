#!/usr/bin/env python3
"""
Seed a rich demo account for hackathon demos.

Creates user 'proofforge_demo' with 3 completed problems and a populated
portfolio card — so judges see a full card without waiting for a live solve.

Usage (from repo root, with docker compose up running):
    python scripts/seed_demo.py
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app import db, minio as minio_module
from app.config import settings  # noqa: F401 — triggers .env load
from app.portfolio.generator import generate_portfolio_card

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)

# ── Demo data ─────────────────────────────────────────────────────────────────

DEMO_USER = {
    "github_id":   "99999001",
    "github_login": "proofforge_demo",
    "name":        "Aryan Singh",
    "email":       "aryan@proofforge.dev",
    "avatar_url":  "https://avatars.githubusercontent.com/u/99999001",
    "career_track": "backend",
    "current_difficulty": "mid",
}

# (slug, score, time_taken_mins)
DEMO_PROBLEMS = [
    ("001-cors-fix",         91, 18),
    ("002-input-validation", 88, 32),
    ("003-memory-leak",      87, 47),
]

REVIEWS = {
    "001-cors-fix": {
        "verdict": "accept",
        "overall_score": 91,
        "summary": (
            "Good understanding of CORS. The specific origin list is correct and "
            "credentials support is a nice touch. Minor: prefer allow_methods=['GET','POST'] "
            "over wildcard in production."
        ),
        "score_breakdown": {
            "correctness": 30,
            "code_quality": 25,
            "security": 20,
            "testing": 16,
        },
        "inline_comments": [
            {
                "file": "starter/main.py",
                "line": 8,
                "severity": "praise",
                "comment": "Correct placement — middleware must be added before route definitions.",
            },
            {
                "file": "starter/main.py",
                "line": 12,
                "severity": "info",
                "comment": "allow_credentials=True is correct for cookie-based auth flows.",
            },
            {
                "file": "starter/main.py",
                "line": 14,
                "severity": "warning",
                "comment": "allow_methods=['*'] is convenient but consider an explicit list in production.",
            },
        ],
        "learning_resources": [
            {
                "title": "FastAPI CORS Middleware docs",
                "url": "https://fastapi.tiangolo.com/tutorial/cors/",
                "relevance": "Official guide to configuring CORSMiddleware",
            },
            {
                "title": "MDN CORS deep-dive",
                "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS",
                "relevance": "Why specific origins are safer than wildcard",
            },
        ],
        "architectural_note": (
            "In a microservice setup, centralise CORS at the API gateway (nginx/Traefik) "
            "rather than each service — reduces drift risk."
        ),
        "ast_score": 95,
        "security_score": 14,
        "test_score": 10,
    },
    "002-input-validation": {
        "verdict": "accept",
        "overall_score": 88,
        "summary": (
            "Correct fix for the Latin-1 encode issue. Well done catching that "
            "bob's password also exposed the bug in your test assertion. "
            "The try/except around the encode is cleaner than a pre-check."
        ),
        "score_breakdown": {
            "correctness": 28,
            "code_quality": 24,
            "security": 20,
            "testing": 16,
        },
        "inline_comments": [
            {
                "file": "starter/auth.py",
                "line": 22,
                "severity": "praise",
                "comment": "Using errors='replace' prevents 500s from any Unicode input.",
            },
            {
                "file": "starter/auth.py",
                "line": 25,
                "severity": "info",
                "comment": "bcrypt handles the byte-string directly — no need for explicit decode.",
            },
            {
                "file": "starter/auth.py",
                "line": 30,
                "severity": "warning",
                "comment": "Log the sanitised username, not the raw input, to avoid log injection.",
            },
            {
                "file": "tests/test_visible.py",
                "line": 41,
                "severity": "praise",
                "comment": "Testing with '日本語' is thorough — covers multi-byte CJK characters.",
            },
        ],
        "learning_resources": [
            {
                "title": "OWASP Input Validation Cheat Sheet",
                "url": "https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html",
                "relevance": "Canonical reference for sanitisation patterns",
            },
            {
                "title": "Python codecs — errors handlers",
                "url": "https://docs.python.org/3/library/codecs.html#error-handlers",
                "relevance": "All error modes explained with examples",
            },
        ],
        "architectural_note": (
            "Validation at the HTTP boundary (Pydantic models) is cleaner than "
            "encoding inside the auth function — moves defence to the perimeter."
        ),
        "ast_score": 90,
        "security_score": 13,
        "test_score": 9,
    },
    "003-memory-leak": {
        "verdict": "accept",
        "overall_score": 87,
        "summary": (
            "Excellent use of TTLCache with a sensible maxsize and TTL. One missed point: "
            "the cache access is not thread-safe under high async concurrency. Adding an "
            "asyncio.Lock() around get/set would make this production-grade."
        ),
        "score_breakdown": {
            "correctness": 27,
            "code_quality": 23,
            "security": 20,
            "testing": 17,
        },
        "inline_comments": [
            {
                "file": "starter/token_store.py",
                "line": 5,
                "severity": "praise",
                "comment": "cachetools.TTLCache is the right tool — bounded size + automatic expiry.",
            },
            {
                "file": "starter/token_store.py",
                "line": 8,
                "severity": "warning",
                "comment": (
                    "Under concurrent async coroutines, a get-then-set pattern is a "
                    "read-modify-write race. Wrap with asyncio.Lock()."
                ),
            },
            {
                "file": "starter/token_store.py",
                "line": 15,
                "severity": "info",
                "comment": "maxsize=10000 is reasonable; document the memory implication (~80 MB peak).",
            },
            {
                "file": "tests/test_visible.py",
                "line": 55,
                "severity": "praise",
                "comment": "The load test loop correctly validates that memory stays bounded.",
            },
        ],
        "learning_resources": [
            {
                "title": "cachetools docs",
                "url": "https://cachetools.readthedocs.io/en/stable/",
                "relevance": "All cache types and thread-safety notes",
            },
            {
                "title": "asyncio synchronisation primitives",
                "url": "https://docs.python.org/3/library/asyncio-sync.html",
                "relevance": "Lock, Semaphore, and Event for concurrent state",
            },
        ],
        "architectural_note": (
            "For a distributed deployment, replace the in-process cache with Redis "
            "(aioredis) — gives you a shared token store across all API replicas."
        ),
        "ast_score": 88,
        "security_score": 12,
        "test_score": 10,
    },
}

# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    await db.init_pool()
    minio_module.init_minio()

    # Check if already seeded
    demo_user = await db.fetchrow(
        "SELECT * FROM users WHERE github_login = $1", DEMO_USER["github_login"]
    )
    if demo_user:
        sub_count = await db.fetchval(
            "SELECT COUNT(*) FROM submissions WHERE user_id = $1", str(demo_user["id"])
        )
        if sub_count and int(sub_count) >= len(DEMO_PROBLEMS):
            logger.info("Demo already seeded (%d submissions). Skipping.", sub_count)
            await db.close_pool()
            return

    # Create or update demo user
    demo_user = await db.fetchrow(
        """
        INSERT INTO users
            (github_id, github_login, name, email, avatar_url,
             career_track, current_difficulty)
        VALUES ($1,$2,$3,$4,$5,$6,$7)
        ON CONFLICT (github_id) DO UPDATE SET
            github_login      = EXCLUDED.github_login,
            name              = EXCLUDED.name,
            career_track      = EXCLUDED.career_track,
            current_difficulty= EXCLUDED.current_difficulty,
            last_active_at    = NOW()
        RETURNING *
        """,
        DEMO_USER["github_id"],
        DEMO_USER["github_login"],
        DEMO_USER["name"],
        DEMO_USER["email"],
        DEMO_USER["avatar_url"],
        DEMO_USER["career_track"],
        DEMO_USER["current_difficulty"],
    )
    user_id = str(demo_user["id"])
    logger.info("Demo user: %s (id=%s)", demo_user["github_login"], user_id)

    total_score = 0

    for slug, score, time_mins in DEMO_PROBLEMS:
        problem = await db.fetchrow(
            "SELECT * FROM problems WHERE slug = $1", slug
        )
        if not problem:
            logger.warning("Problem %s not found — run 002_seed_problems.py first", slug)
            continue

        problem_id = str(problem["id"])

        # Session
        session_id = await db.fetchval(
            """
            INSERT INTO active_sessions (user_id, problem_id, status)
            VALUES ($1, $2, 'completed')
            ON CONFLICT (user_id, problem_id) DO UPDATE SET status='completed'
            RETURNING id
            """,
            user_id, problem_id,
        )

        # Submission
        review_data = REVIEWS[slug]
        fake_code = {
            "starter/main.py": "# Demo solution\n",
            "starter/__init__.py": "",
        }

        existing_sub = await db.fetchrow(
            "SELECT id FROM submissions WHERE user_id=$1 AND problem_id=$2",
            user_id, problem_id,
        )
        if existing_sub:
            submission_id = str(existing_sub["id"])
        else:
            submission_id = str(await db.fetchval(
                """
                INSERT INTO submissions
                    (user_id, problem_id, session_id, status, code_snapshot,
                     score, attempt_number, time_taken_mins, submitted_at, completed_at)
                VALUES ($1,$2,$3,'completed',$4,$5,1,$6,NOW(),NOW())
                RETURNING id
                """,
                user_id, problem_id, str(session_id),
                json.dumps(fake_code),
                score, time_mins,
            ))

        # Review
        existing_review = await db.fetchrow(
            "SELECT id FROM reviews WHERE submission_id = $1", submission_id
        )
        if not existing_review:
            review_id = await db.fetchval(
                """
                INSERT INTO reviews (
                    submission_id, verdict, overall_score, score_breakdown,
                    summary, inline_comments, learning_resources, architectural_note,
                    ast_score, security_score, test_score, pipeline_duration_ms
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                RETURNING id
                """,
                submission_id,
                review_data["verdict"],
                review_data["overall_score"],
                json.dumps(review_data["score_breakdown"]),
                review_data["summary"],
                json.dumps(review_data["inline_comments"]),
                json.dumps(review_data["learning_resources"]),
                review_data["architectural_note"],
                review_data["ast_score"],
                review_data["security_score"],
                review_data["test_score"],
                1200,
            )
            # Link review to submission
            await db.execute(
                "UPDATE submissions SET review_id = $1 WHERE id = $2",
                str(review_id), submission_id,
            )

        total_score += score
        logger.info("  Seeded %s — score=%d, time=%dmin", slug, score, time_mins)

    # Update user stats
    await db.execute(
        """
        UPDATE users
        SET issues_resolved = $1,
            total_score     = $2,
            current_difficulty = 'mid',
            last_active_at  = NOW()
        WHERE id = $3
        """,
        len(DEMO_PROBLEMS), total_score, user_id,
    )

    # Generate portfolio card
    logger.info("Generating portfolio card...")
    card = await generate_portfolio_card(user_id)
    logger.info(
        "Portfolio card generated — %d issues, avg_score=%.1f",
        card["issues_resolved"], card["avg_score"],
    )

    await db.close_pool()

    print("\n" + "=" * 60)
    print("Demo seeded successfully!")
    print(f"Portfolio: http://localhost:8000/api/v1/portfolio/{DEMO_USER['github_login']}")
    print(f"Frontend:  http://localhost:5173/p/{DEMO_USER['github_login']}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
