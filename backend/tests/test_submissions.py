"""
Submission API + WebSocket integration tests.

Sandbox-dependent tests (test_full_pipeline, test_websocket_receives_updates) are
skipped when Docker is unavailable, mirroring test_sandbox.py.
"""
import asyncio
import json
import secrets
import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect
from jose import jwt

from app.config import settings


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_jwt(user_id: str, github_login: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": user_id,
            "github_login": github_login,
            "jti": secrets.token_hex(16),
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        settings.JWT_SECRET,
        algorithm="HS256",
    )


async def _seed_user_problem_session(
    db_conn: asyncpg.Connection,
) -> tuple[dict, dict, dict]:
    """Insert one user, one problem, and one active session; return all three as dicts."""
    user = await db_conn.fetchrow(
        """INSERT INTO users (github_id, github_login, name)
           VALUES ($1, $2, $3) RETURNING *""",
        "gh_sub_test_001", "sub_test_user", "Submission Test User",
    )
    problem = await db_conn.fetchrow(
        """INSERT INTO problems (
               slug, title, description, difficulty, category, track, language,
               docker_image, codebase_key, test_suite_key, time_limit_mins, points,
               display_order, is_active
           ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,TRUE) RETURNING *""",
        "001-cors-fix",
        "Fix CORS",
        "Add CORSMiddleware",
        "junior",
        "api",
        "backend",
        "python",
        "proofforge/python-runner:3.12",
        "starters/001-cors-fix.tar.gz",
        "tests/001-cors-fix.tar.gz",
        20,
        100,
        1,
    )
    session = await db_conn.fetchrow(
        """INSERT INTO active_sessions (user_id, problem_id)
           VALUES ($1, $2) RETURNING *""",
        user["id"], problem["id"],
    )
    return dict(user), dict(problem), dict(session)


BROKEN_CORS_FILES = {
    "starter/__init__.py": "",
    "starter/main.py": (
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n\n"
        "@app.get('/api/users')\n"
        "async def get_users(): return []\n"
    ),
}

FIXED_CORS_FILES = {
    "starter/__init__.py": "",
    "starter/main.py": (
        "from fastapi import FastAPI\n"
        "from fastapi.middleware.cors import CORSMiddleware\n\n"
        "app = FastAPI()\n"
        "app.add_middleware(\n"
        "    CORSMiddleware,\n"
        "    allow_origins=['*'],\n"
        "    allow_methods=['*'],\n"
        "    allow_headers=['*'],\n"
        ")\n\n"
        "MOCK_USERS = [\n"
        "    {'id': 1, 'username': 'alice', 'email': 'alice@example.com'},\n"
        "]\n\n"
        "@app.get('/api/users')\n"
        "async def get_users(): return MOCK_USERS\n\n"
        "@app.get('/api/health')\n"
        "async def health(): return {'status': 'ok'}\n\n"
        "@app.post('/api/login')\n"
        "async def login(payload: dict): return {'token': 'mock-token-abc123'}\n"
    ),
}

# Minimal fake sandbox result for mocking
FAKE_TEST_RESULTS = {
    "session_id": "fake-session",
    "status": "completed",
    "passed": 2,
    "failed": 0,
    "total": 2,
    "duration_ms": 500,
    "tests": [
        {"name": "test_cors_headers_present", "status": "passed", "duration_ms": 200, "error": None},
        {"name": "test_get_users_with_cors", "status": "passed", "duration_ms": 300, "error": None},
    ],
}

FAKE_REVIEW = {
    "verdict": "accept",
    "overall_score": 90,
    "score_breakdown": {
        "correctness": 28, "code_quality": 22, "performance": 18, "security": 12, "tests": 10,
    },
    "summary": "Great fix. CORS middleware correctly configured.",
    "inline_comments": [
        {
            "file": "starter/main.py",
            "line": 5,
            "severity": "praise",
            "comment": "Using CORSMiddleware is the idiomatic FastAPI approach and solves the cross-origin issue completely.",
        }
    ],
    "learning_resources": [
        {
            "title": "FastAPI CORS docs",
            "url": "https://fastapi.tiangolo.com/tutorial/cors/",
            "why": "Covers exactly the CORSMiddleware pattern used in this fix.",
        }
    ],
    "architectural_note": None,
}


# ── run-tests endpoint ─────────────────────────────────────────────────────────

async def test_run_tests_endpoint(client: TestClient, db_conn: asyncpg.Connection):
    """POST run-tests with broken code returns failed test results."""
    user, problem, session = await _seed_user_problem_session(db_conn)
    token = _make_jwt(str(user["id"]), user["github_login"])

    fake_result = {
        "session_id": "x",
        "status": "completed",
        "passed": 0,
        "failed": 2,
        "total": 2,
        "duration_ms": 300,
        "tests": [
            {"name": "test_cors_headers_present", "status": "failed", "duration_ms": 100, "error": "AssertionError"},
            {"name": "test_get_users_with_cors", "status": "failed", "duration_ms": 200, "error": "AssertionError"},
        ],
    }

    with patch("app.submissions.router.sandbox_runner") as mock_runner:
        mock_runner.run_tests = AsyncMock(return_value=fake_result)

        resp = client.post(
            f"/api/v1/sessions/{session['id']}/run-tests",
            json={"files": BROKEN_CORS_FILES},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["failed"] >= 1
    assert data["status"] == "completed"


async def test_run_tests_rate_limit(client: TestClient, db_conn: asyncpg.Connection):
    """POST run-tests more than 10 times returns 429 on the 11th call."""
    user, problem, session = await _seed_user_problem_session(db_conn)
    token = _make_jwt(str(user["id"]), user["github_login"])

    fake_result = {
        "session_id": "x", "status": "completed",
        "passed": 0, "failed": 0, "total": 0, "duration_ms": 10, "tests": [],
    }

    with patch("app.submissions.router.sandbox_runner") as mock_runner:
        mock_runner.run_tests = AsyncMock(return_value=fake_result)

        for _ in range(10):
            r = client.post(
                f"/api/v1/sessions/{session['id']}/run-tests",
                json={"files": BROKEN_CORS_FILES},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

        # 11th call must be rate-limited
        r11 = client.post(
            f"/api/v1/sessions/{session['id']}/run-tests",
            json={"files": BROKEN_CORS_FILES},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r11.status_code == 429
    assert "Maximum test runs" in r11.json()["detail"]


# ── submit endpoint ───────────────────────────────────────────────────────────

async def test_submit_returns_202(client: TestClient, db_conn: asyncpg.Connection):
    """POST /submissions returns 202 with a submission_id immediately."""
    user, problem, session = await _seed_user_problem_session(db_conn)
    token = _make_jwt(str(user["id"]), user["github_login"])

    # Patch the background task so it doesn't actually run
    with patch("app.submissions.router._process_submission", new_callable=AsyncMock):
        resp = client.post(
            "/api/v1/submissions",
            json={"session_id": str(session["id"]), "files": FIXED_CORS_FILES},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert "submission_id" in data
    assert data["status"] == "queued"


# ── WebSocket tests ───────────────────────────────────────────────────────────

async def test_websocket_receives_updates(client: TestClient, db_conn: asyncpg.Connection):
    """Connect to WS for a queued submission; mock pipeline sends status_update events."""
    user, problem, session = await _seed_user_problem_session(db_conn)
    token = _make_jwt(str(user["id"]), user["github_login"])

    # Create a queued submission directly
    submission_id = await db_conn.fetchval(
        """INSERT INTO submissions (user_id, problem_id, session_id, status, code_snapshot)
           VALUES ($1,$2,$3,'queued',$4) RETURNING id""",
        user["id"], problem["id"], session["id"], json.dumps(FIXED_CORS_FILES),
    )

    received: list[dict] = []

    def _ws_client():
        with client.websocket_connect(
            f"/api/v1/ws/submissions/{submission_id}?token={token}"
        ) as ws:
            try:
                # Collect up to 3 messages with a short timeout
                for _ in range(3):
                    msg = ws.receive_text()
                    received.append(json.loads(msg))
            except Exception:
                pass

    ws_thread = threading.Thread(target=_ws_client, daemon=True)
    ws_thread.start()

    # Give the WS time to connect then publish messages via Redis
    await asyncio.sleep(0.3)
    from app.redis import get_redis
    redis = get_redis()
    channel = f"submission:{submission_id}"

    await redis.publish(channel, json.dumps({
        "type": "status_update",
        "status": "running_tests",
        "message": "Running test suite...",
        "submission_id": str(submission_id),
    }))
    await asyncio.sleep(0.1)
    await redis.publish(channel, json.dumps({
        "type": "review_complete",
        "submission_id": str(submission_id),
        "score": 90,
        "verdict": "accept",
        "review_id": "fake-review-id",
    }))

    ws_thread.join(timeout=5)

    types = [m.get("type") for m in received]
    assert "status_update" in types or "review_complete" in types, (
        f"Expected WS messages, got: {received}"
    )


async def test_full_pipeline(client: TestClient, db_conn: asyncpg.Connection):
    """
    Submit correct CORS fix, mock the sandbox + Claude, assert:
    - submission created (202)
    - GET /submissions/{id} eventually shows status=completed
    - GET /submissions/{id}/review returns full review JSON with inline_comments
    """
    user, problem, session = await _seed_user_problem_session(db_conn)
    token = _make_jwt(str(user["id"]), user["github_login"])
    auth = {"Authorization": f"Bearer {token}"}

    with (
        patch("app.submissions.router.sandbox_runner") as mock_runner,
        patch("app.submissions.router.review_pipeline") as mock_rp,
        patch("app.submissions.router.minio_module") as mock_minio,
    ):
        mock_runner.run_tests = AsyncMock(return_value=FAKE_TEST_RESULTS)
        mock_rp.run_ast_analysis = AsyncMock(return_value={
            "anti_patterns": [], "max_complexity": 3, "max_nesting": 2, "overall_ast_score": 95,
        })
        mock_rp.run_security_scan = AsyncMock(return_value={
            "findings": [], "security_score": 15,
        })
        mock_rp.call_claude_review = AsyncMock(return_value=FAKE_REVIEW)
        mock_minio.download_file.return_value = b""  # empty tar — diff will show "no diff"
        mock_minio.PROBLEMS_BUCKET = "problems"

        resp = client.post(
            "/api/v1/submissions",
            json={"session_id": str(session["id"]), "files": FIXED_CORS_FILES},
            headers=auth,
        )
        assert resp.status_code == 202, resp.text
        submission_id = resp.json()["submission_id"]

        # The background task runs; wait for it to complete (max 10s)
        for _ in range(50):
            await asyncio.sleep(0.2)
            status_resp = client.get(
                f"/api/v1/submissions/{submission_id}", headers=auth
            )
            if status_resp.json().get("status") == "completed":
                break
        else:
            pytest.fail(
                f"Submission did not reach 'completed' in time. "
                f"Last status: {status_resp.json()}"
            )

    # Check status endpoint
    status_resp = client.get(f"/api/v1/submissions/{submission_id}", headers=auth)
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["status"] == "completed"
    assert data["score"] > 0
    assert data["review_id"] is not None

    # Check review endpoint
    review_resp = client.get(
        f"/api/v1/submissions/{submission_id}/review", headers=auth
    )
    assert review_resp.status_code == 200
    review = review_resp.json()
    assert review["verdict"] == "accept"
    assert review["overall_score"] == 90
    assert "score_breakdown" in review
    assert isinstance(review["inline_comments"], list)
    assert len(review["inline_comments"]) >= 1
    assert "learning_resources" in review
