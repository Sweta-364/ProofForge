"""
Full end-to-end integration test.

Requires:
  - All Docker services running  (docker compose up)
  - Problems seeded              (python backend/migrations/002_seed_problems.py)
  - Docker daemon accessible     (for the sandbox container)

Skipped automatically when Docker is not available.
"""
import base64
import secrets
import time
from datetime import datetime, timedelta, timezone

import asyncpg
import nacl.signing  # type: ignore[import]
import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.config import settings

# ── Docker availability guard ─────────────────────────────────────────────────

def _docker_available() -> bool:
    try:
        import docker
        docker.from_env().ping()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _docker_available(),
    reason="Docker daemon not available — skipping integration test",
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_token(user_id: str, github_login: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "github_login": github_login,
        "jti": secrets.token_hex(16),
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── Starter and fixed code for 001-cors-fix ───────────────────────────────────

BROKEN_CODE = {
    "starter/__init__.py": "",
    "starter/main.py": """\
from fastapi import FastAPI

app = FastAPI()

@app.get("/api/users")
async def get_users():
    return [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.post("/api/login")
async def login(data: dict):
    return {"token": "fake-token"}
""",
}

FIXED_CODE = {
    "starter/__init__.py": "",
    "starter/main.py": """\
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/users")
async def get_users():
    return [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.post("/api/login")
async def login(data: dict):
    return {"token": "fake-token"}
""",
}


# ── Signing key for portfolio verify ─────────────────────────────────────────

@pytest.fixture(scope="module", autouse=True)
def patch_signing_key():
    sk = nacl.signing.SigningKey.generate()
    private_b64 = base64.b64encode(bytes(sk)).decode()
    original = settings.PORTFOLIO_SIGNING_PRIVATE_KEY
    settings.PORTFOLIO_SIGNING_PRIVATE_KEY = private_b64
    yield
    settings.PORTFOLIO_SIGNING_PRIVATE_KEY = original


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def integration_user(db_conn: asyncpg.Connection):
    """Synchronous wrapper — conftest truncates tables between tests."""
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        db_conn.fetchrow(
            """
            INSERT INTO users (github_id, github_login, name, career_track)
            VALUES ('integ-001', 'integtester', 'Integration Tester', 'backend')
            RETURNING *
            """
        )
    )


# ── THE TEST ──────────────────────────────────────────────────────────────────

def test_full_loop(client: TestClient, db_conn: asyncpg.Connection):
    """
    Login → set track → get problem → run broken tests → run fixed tests
    → submit → poll → review → portfolio → verify.
    """
    import asyncio
    loop = asyncio.get_event_loop()

    # ── 1. Create user + token ────────────────────────────────────────────────
    user = loop.run_until_complete(
        db_conn.fetchrow(
            """
            INSERT INTO users (github_id, github_login, name)
            VALUES ('integ-gh-001', 'integtester', 'Integration Tester')
            RETURNING *
            """
        )
    )
    user_id = str(user["id"])
    token = _make_token(user_id, "integtester")

    # ── 2. Set career track ───────────────────────────────────────────────────
    resp = client.put(
        "/api/v1/users/me/track",
        json={"track": "backend"},
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["career_track"] == "backend"

    # ── 2b. Seed the problem row ──────────────────────────────────────────────
    # truncate_tables wipes `problems` after every test, so a full-suite run
    # reaches this test with an empty table. The MinIO tarballs persist
    # (002_seed_problems.py); only the DB row must be recreated here.
    loop.run_until_complete(
        db_conn.execute(
            """
            INSERT INTO problems
                (slug, title, description, difficulty, category, track, language,
                 docker_image, codebase_key, test_suite_key, time_limit_mins,
                 points, display_order, is_active)
            VALUES
                ('001-cors-fix', 'Fix CORS', 'Add CORSMiddleware', 'junior',
                 'configuration', 'fullstack', 'python',
                 'proofforge/python-runner:3.12',
                 'starters/001-cors-fix.tar.gz', 'tests/001-cors-fix.tar.gz',
                 30, 100, 1, TRUE)
            ON CONFLICT (slug) DO NOTHING
            """
        )
    )

    # ── 3. Get current problem ────────────────────────────────────────────────
    resp = client.get("/api/v1/problems/current", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    session_id = data["session_id"]
    problem = data["problem"]
    assert problem["slug"] == "001-cors-fix"
    # Starter files must be present (MinIO seeded)
    assert "starter/main.py" in problem["files"]

    # ── 4. Run broken starter code → some tests fail ──────────────────────────
    resp = client.post(
        f"/api/v1/sessions/{session_id}/run-tests",
        json={"files": BROKEN_CODE},
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    run_result = resp.json()
    assert run_result["failed"] >= 1, "Expected at least 1 failure on broken code"

    # ── 5. Run fixed code → all tests pass ────────────────────────────────────
    resp = client.post(
        f"/api/v1/sessions/{session_id}/run-tests",
        json={"files": FIXED_CODE},
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    run_result = resp.json()
    assert run_result["failed"] == 0, f"Expected 0 failures on fixed code, got: {run_result}"

    # ── 6. Submit ─────────────────────────────────────────────────────────────
    resp = client.post(
        "/api/v1/submissions",
        json={"session_id": session_id, "files": FIXED_CODE},
        headers=_auth(token),
    )
    assert resp.status_code == 202, resp.text
    submission_id = resp.json()["submission_id"]
    assert submission_id

    # ── 7. Poll until completed (max 90 seconds) ──────────────────────────────
    status = "queued"
    deadline = time.time() + 90
    while time.time() < deadline:
        time.sleep(3)
        resp = client.get(
            f"/api/v1/submissions/{submission_id}",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        status = resp.json()["status"]
        if status in ("completed", "failed"):
            break

    assert status == "completed", f"Submission timed out or failed — final status: {status}"

    sub_data = resp.json()
    assert sub_data["score"] is not None
    assert sub_data["score"] > 0, f"Expected score > 0, got {sub_data['score']}"

    # ── 8. Get the review ─────────────────────────────────────────────────────
    resp = client.get(
        f"/api/v1/submissions/{submission_id}/review",
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    review = resp.json()
    assert review["verdict"] in ("accept", "minor_revisions", "major_revisions")
    assert isinstance(review["inline_comments"], list)
    assert review["overall_score"] > 0

    # ── 9. Get portfolio ──────────────────────────────────────────────────────
    resp = client.get("/api/v1/portfolio/integtester")
    assert resp.status_code == 200, resp.text
    portfolio = resp.json()
    assert portfolio["issues_resolved"] == 1
    assert any(v > 0 for v in portfolio["skill_radar"].values()), \
        "skill_radar should have at least one non-zero value"

    # ── 10. Verify portfolio signature ────────────────────────────────────────
    resp = client.get("/api/v1/portfolio/integtester/verify")
    assert resp.status_code == 200, resp.text
    verify = resp.json()
    assert verify["valid"] is True, f"Portfolio verify failed: {verify}"
