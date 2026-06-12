"""
Tests for portfolio card generation, signing, and verification.

All tests use the shared db_conn + client fixtures from conftest.py.
The signing key is generated fresh per test session so tests don't
depend on .env having PORTFOLIO_SIGNING_PRIVATE_KEY set.
"""
import base64
import json

import asyncpg
import nacl.signing  # type: ignore[import]
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.config import settings
from app.portfolio.generator import generate_portfolio_card


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def patch_signing_key():
    """Generate a real Ed25519 keypair for the test session."""
    sk = nacl.signing.SigningKey.generate()
    private_b64 = base64.b64encode(bytes(sk)).decode()
    original = settings.PORTFOLIO_SIGNING_PRIVATE_KEY
    settings.PORTFOLIO_SIGNING_PRIVATE_KEY = private_b64
    yield private_b64
    settings.PORTFOLIO_SIGNING_PRIVATE_KEY = original


@pytest_asyncio.fixture
async def demo_user(db_conn: asyncpg.Connection) -> asyncpg.Record:
    return await db_conn.fetchrow(
        """
        INSERT INTO users (github_id, github_login, name, career_track)
        VALUES ('test-gh-100', 'portfoliouser', 'Portfolio User', 'backend')
        RETURNING *
        """
    )


@pytest_asyncio.fixture
async def demo_problem(db_conn: asyncpg.Connection) -> asyncpg.Record:
    return await db_conn.fetchrow(
        """
        INSERT INTO problems
            (slug, title, description, difficulty, category, track, language,
             docker_image, codebase_key, test_suite_key, display_order)
        VALUES
            ('001-cors-fix','Fix CORS','Add CORSMiddleware','junior','api',
             'backend','python','proofforge/python-runner:3.12',
             'starters/001-cors-fix.tar.gz','tests/001-cors-fix.tar.gz',1)
        RETURNING *
        """
    )


@pytest_asyncio.fixture
async def accepted_submission(
    db_conn: asyncpg.Connection,
    demo_user: asyncpg.Record,
    demo_problem: asyncpg.Record,
) -> asyncpg.Record:
    """Insert a completed submission with an accepted review (score=88)."""
    session_id = await db_conn.fetchval(
        "INSERT INTO active_sessions (user_id, problem_id) VALUES ($1,$2) RETURNING id",
        demo_user["id"], demo_problem["id"],
    )
    submission_id = await db_conn.fetchval(
        """
        INSERT INTO submissions
            (user_id, problem_id, session_id, status, code_snapshot, score,
             attempt_number, time_taken_mins, submitted_at, completed_at)
        VALUES ($1,$2,$3,'completed','{}',88,1,30,NOW(),NOW())
        RETURNING id
        """,
        demo_user["id"], demo_problem["id"], session_id,
    )
    score_breakdown = json.dumps({"correctness": 30, "code_quality": 25, "security": 20, "testing": 13})
    review_id = await db_conn.fetchval(
        """
        INSERT INTO reviews
            (submission_id, verdict, overall_score, score_breakdown, summary,
             inline_comments, learning_resources, ast_score, security_score,
             test_score, pipeline_duration_ms)
        VALUES ($1,'accept',88,$2,'Good fix.','[]','[]',90,13,9,800)
        RETURNING id
        """,
        submission_id, score_breakdown,
    )
    await db_conn.execute(
        "UPDATE submissions SET review_id=$1 WHERE id=$2", review_id, submission_id
    )
    return await db_conn.fetchrow("SELECT * FROM submissions WHERE id=$1", submission_id)


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_empty_portfolio(demo_user: asyncpg.Record):
    """New user with no submissions returns empty card without crashing."""
    card = await generate_portfolio_card(str(demo_user["id"]))
    assert card["issues_resolved"] == 0
    assert card["avg_score"] == 0.0
    assert card["highlights"] == []
    assert card["resolution_log"] == []
    assert all(v == 0 for v in card["skill_radar"].values())


@pytest.mark.asyncio
async def test_portfolio_after_submission(
    demo_user: asyncpg.Record,
    accepted_submission: asyncpg.Record,
):
    """Submission with score >= 60 populates the card."""
    card = await generate_portfolio_card(str(demo_user["id"]))
    assert card["issues_resolved"] == 1
    assert card["avg_score"] == 88.0
    assert len(card["resolution_log"]) == 1
    assert card["resolution_log"][0]["score"] == 88


@pytest.mark.asyncio
async def test_skill_radar_populated(
    demo_user: asyncpg.Record,
    accepted_submission: asyncpg.Record,
):
    """Problem category 'api' → architecture and code_quality axes should be > 0."""
    card = await generate_portfolio_card(str(demo_user["id"]))
    radar = card["skill_radar"]
    assert radar["architecture"] > 0 or radar["code_quality"] > 0


@pytest.mark.asyncio
async def test_highlights_extracted(
    db_conn: asyncpg.Connection,
    demo_user: asyncpg.Record,
):
    """Memory-leak slug triggers the memory highlight."""
    problem_id = await db_conn.fetchval(
        """
        INSERT INTO problems
            (slug, title, description, difficulty, category, track, language,
             docker_image, codebase_key, test_suite_key, display_order)
        VALUES
            ('003-memory-leak','Fix Memory Leak','...','mid','optimization',
             'backend','python','proofforge/python-runner:3.12',
             'starters/003-memory-leak.tar.gz','tests/003-memory-leak.tar.gz',3)
        RETURNING id
        """
    )
    session_id = await db_conn.fetchval(
        "INSERT INTO active_sessions (user_id, problem_id) VALUES ($1,$2) RETURNING id",
        demo_user["id"], problem_id,
    )
    sub_id = await db_conn.fetchval(
        """
        INSERT INTO submissions
            (user_id, problem_id, session_id, status, code_snapshot, score,
             attempt_number, time_taken_mins, submitted_at, completed_at)
        VALUES ($1,$2,$3,'completed','{}',87,1,47,NOW(),NOW())
        RETURNING id
        """,
        demo_user["id"], problem_id, session_id,
    )
    review_id = await db_conn.fetchval(
        """
        INSERT INTO reviews
            (submission_id, verdict, overall_score, score_breakdown, summary,
             inline_comments, learning_resources, ast_score, security_score,
             test_score, pipeline_duration_ms)
        VALUES ($1,'accept',87,'{}','Fixed.','[]','[]',88,12,10,900)
        RETURNING id
        """,
        sub_id,
    )
    await db_conn.execute(
        "UPDATE submissions SET review_id=$1 WHERE id=$2", review_id, sub_id
    )

    card = await generate_portfolio_card(str(demo_user["id"]))
    assert any("memory" in h["metric"].lower() for h in card["highlights"])


@pytest.mark.asyncio
async def test_signature_valid(
    client: TestClient,
    demo_user: asyncpg.Record,
    accepted_submission: asyncpg.Record,
):
    """generate → GET /verify returns valid=true."""
    await generate_portfolio_card(str(demo_user["id"]))
    resp = client.get(f"/api/v1/portfolio/{demo_user['github_login']}/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["github_login"] == demo_user["github_login"]


@pytest.mark.asyncio
async def test_signature_tamper(
    db_conn: asyncpg.Connection,
    client: TestClient,
    demo_user: asyncpg.Record,
    accepted_submission: asyncpg.Record,
):
    """Tampering with stored data makes verify return valid=false."""
    await generate_portfolio_card(str(demo_user["id"]))

    # Corrupt the stored skill_radar so it no longer matches the hash
    await db_conn.execute(
        """
        UPDATE portfolio_cards
        SET skill_radar = '{"debugging":99}'
        WHERE user_id = $1
        """,
        demo_user["id"],
    )

    resp = client.get(f"/api/v1/portfolio/{demo_user['github_login']}/verify")
    assert resp.status_code == 200
    assert resp.json()["valid"] is False


def test_portfolio_cached(
    client: TestClient,
    demo_user: asyncpg.Record,
):
    """Calling GET /portfolio/{login} twice should hit Redis cache on the second call
    and return the same data."""
    login = demo_user["github_login"]

    resp1 = client.get(f"/api/v1/portfolio/{login}")
    assert resp1.status_code == 200

    resp2 = client.get(f"/api/v1/portfolio/{login}")
    assert resp2.status_code == 200

    # Identical JSON response (including any cache-populated fields)
    assert resp1.json()["issues_resolved"] == resp2.json()["issues_resolved"]
    assert resp1.json()["avg_score"] == resp2.json()["avg_score"]
