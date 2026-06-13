"""
Personalized problem generation using the configured OpenAI-compatible LLM
(defaults to Groq / llama-3.3-70b-versatile via DEV_LLM_* settings).

Calls the LLM with a structured JSON prompt, validates the output, packs
starter + test files into tar.gz, uploads to MinIO, and inserts a problems
row with owner_user_id set so the problem only appears in the creator's
dashboard.

LangChain/LangGraph are intentionally NOT used — the workflow is a linear
pipeline that doesn't need a graph abstraction.
"""
import asyncio
import json
import logging
import uuid

import httpx

from app import db
from app import minio as minio_module
from app.config import settings
from app.tar_utils import create_tar_from_dict

logger = logging.getLogger(__name__)

# ── Prompt ────────────────────────────────────────────────────────────────────

_SYSTEM = """\
You are an expert Python/FastAPI coding challenge designer for ProofForge, a developer skills \
platform. Generate a realistic, production-style problem consisting of a BROKEN FastAPI \
application that a developer must debug and fix.

HARD RULES:
1. The starter code MUST contain exactly one clear, specific bug related to the requested topic.
2. Tests MUST fail on the broken starter code, and MUST pass after the correct fix is applied.
3. Tests use pytest with FastAPI TestClient. Import the app as: from starter.main import app
4. The sandbox has NO network access and NO external services (no real database, Redis,
   or HTTP calls). The app and tests MUST be fully self-contained and run offline.
   Available packages ONLY: fastapi, starlette, pydantic, httpx, python-multipart
   (form/file uploads work), email-validator, itsdangerous, jinja2, pyyaml, cachetools,
   python-jose, PyJWT, bcrypt, aiofiles, and the Python standard library.
   Never import redis, celery, requests, or connect to any database or network resource.
5. starter/requirements.txt must list only the packages the starter code actually imports.
   For uploads, include python-multipart; for EmailStr, include email-validator.
5b. Tests MUST NOT read from or write to disk — the sandbox filesystem is read-only.
   Never call open(...) for writing. To test file uploads, pass in-memory bytes directly:
   client.post("/upload", files={"file": ("name.txt", b"file content here", "text/plain")}).
   Build all request payloads inline; do not create temp files.
6. difficulty rules:
   - "junior": single obvious bug, 1-3 lines to fix
   - "mid":    subtle logic error, 5-15 lines to fix
   - "senior": architectural/async issue, multiple coordinated changes required
7. description must be written as a realistic GitHub issue in markdown — include:
   - What was expected vs what actually happens
   - Steps to reproduce (curl commands or code)
   - Acceptance criteria
8. optimal_hint is a private reviewer note (NOT shown to the student) explaining the exact fix.
9. docker_image must always be exactly: proofforge/python-runner:3.12
10. track must be "backend" for Python/FastAPI problems.
11. category must be one of: configuration, validation, security, performance, async, \
database, testing, caching, auth.

REQUIRED OUTPUT — respond with ONLY a single JSON object, no markdown fences, no extra text:
{
  "title": "<concise GitHub-issue-style title, max 80 chars>",
  "description": "<GitHub issue markdown, 150-300 words>",
  "difficulty": "junior" | "mid" | "senior",
  "category": "<one of the listed categories>",
  "track": "backend",
  "docker_image": "proofforge/python-runner:3.12",
  "time_limit_mins": <30 for junior, 45 for mid, 60 for senior>,
  "points": <100 for junior, 150 for mid, 200 for senior>,
  "optimal_hint": "<2-3 sentence private note for the AI code reviewer>",
  "starter_files": {
    "starter/__init__.py": "",
    "starter/main.py": "<complete broken FastAPI app, at least 40 lines>",
    "starter/requirements.txt": "<one package per line>"
  },
  "test_files": {
    "tests/__init__.py": "",
    "tests/test_visible.py": "<EXACTLY 2 pytest functions using TestClient that fail on the broken code and pass after the fix>",
    "tests/hidden/__init__.py": "",
    "tests/hidden/test_edge.py": "<EXACTLY 2 pytest edge-case functions>"
  }
}
"""

# ── Validation ────────────────────────────────────────────────────────────────

_REQUIRED_TOP = [
    "title", "description", "difficulty", "category", "track",
    "docker_image", "time_limit_mins", "points", "optimal_hint",
    "starter_files", "test_files",
]
_VALID_DIFFICULTIES = {"junior", "mid", "senior"}
_VALID_CATEGORIES = {
    "configuration", "validation", "security", "performance",
    "async", "database", "testing", "caching", "auth",
}
_REQUIRED_STARTER = {"starter/__init__.py", "starter/main.py", "starter/requirements.txt"}
_REQUIRED_TESTS = {
    "tests/__init__.py",
    "tests/test_visible.py",
    "tests/hidden/__init__.py",
    "tests/hidden/test_edge.py",
}


def _validate(data: dict) -> None:
    for field in _REQUIRED_TOP:
        if field not in data:
            raise ValueError(f"AI output missing required field: '{field}'")

    if data["difficulty"] not in _VALID_DIFFICULTIES:
        raise ValueError(f"Invalid difficulty '{data['difficulty']}' — must be junior/mid/senior")

    if data["category"] not in _VALID_CATEGORIES:
        raise ValueError(f"Invalid category '{data['category']}'")

    if not isinstance(data.get("starter_files"), dict):
        raise ValueError("'starter_files' must be an object")
    if not isinstance(data.get("test_files"), dict):
        raise ValueError("'test_files' must be an object")

    missing_s = _REQUIRED_STARTER - set(data["starter_files"])
    if missing_s:
        raise ValueError(f"Missing required starter files: {missing_s}")

    missing_t = _REQUIRED_TESTS - set(data["test_files"])
    if missing_t:
        raise ValueError(f"Missing required test files: {missing_t}")

    main_py = data["starter_files"].get("starter/main.py", "")
    if len(main_py.strip()) < 40:
        raise ValueError("starter/main.py is too short — generation may have failed")


# ── LLM call via OpenAI-compatible API (synchronous — wrapped in asyncio.to_thread) ──

def _call_openai_compat(topic: str) -> dict:
    """Call the configured OpenAI-compatible endpoint (Groq by default) synchronously."""
    payload = {
        "model": settings.DEV_LLM_MODEL,
        "max_tokens": 8192,
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": f"Generate a coding problem about: {topic}"},
        ],
    }
    with httpx.Client(timeout=120) as client:
        resp = client.post(
            f"{settings.DEV_LLM_BASE_URL}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {settings.DEV_LLM_API_KEY}"},
        )
        resp.raise_for_status()

    raw = resp.json()["choices"][0]["message"]["content"]
    # Strip markdown fences if the model wraps JSON (same handling as review_pipeline.py)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0].strip()
    return json.loads(raw)


# ── Public API ─────────────────────────────────────────────────────────────────

async def generate_problem_for_user(
    topic: str,
    user_id: str,
    github_login: str,
) -> dict:
    """
    Full pipeline: LLM → validate → MinIO → DB insert.
    Returns dict with problem_id and slug for the caller to open a session.
    """
    if not settings.DEV_LLM_API_KEY:
        raise RuntimeError(
            "DEV_LLM_API_KEY is not set. Add your free Groq key (console.groq.com) to .env."
        )

    logger.info("Generating problem for user=%s topic=%r", user_id[:8], topic)

    try:
        data = await asyncio.to_thread(_call_openai_compat, topic)
    except json.JSONDecodeError as exc:
        logger.error("LLM returned non-JSON: %s", exc)
        raise ValueError("AI returned malformed output — please try rephrasing your topic")
    except Exception as exc:
        logger.error("LLM API error: %s", exc)
        raise RuntimeError(f"Problem generation failed: {exc}")

    _validate(data)

    slug = f"gen-{github_login}-{uuid.uuid4().hex[:8]}"

    starter_tar = create_tar_from_dict(data["starter_files"])
    # Strip the leading "tests/" prefix — the sandbox runner extracts the test tar
    # into an already-named "tests/" directory, so paths must be relative to that dir.
    tests_tar = create_tar_from_dict({
        path.removeprefix("tests/"): content
        for path, content in data["test_files"].items()
    })
    starter_key = f"starters/{slug}.tar.gz"
    tests_key = f"tests/{slug}.tar.gz"

    # MinIO SDK is synchronous — run in thread pool
    await asyncio.to_thread(
        minio_module.upload_bytes, minio_module.PROBLEMS_BUCKET, starter_key, starter_tar,
    )
    await asyncio.to_thread(
        minio_module.upload_bytes, minio_module.PROBLEMS_BUCKET, tests_key, tests_tar,
    )
    logger.info("Uploaded %s and %s", starter_key, tests_key)

    problem_id = await db.fetchval(
        """
        INSERT INTO problems (
            slug, title, description, difficulty, category, track, language,
            docker_image, codebase_key, test_suite_key, time_limit_mins, points,
            display_order, is_active, optimal_hint, owner_user_id
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,9999,TRUE,$13,$14::uuid)
        RETURNING id
        """,
        slug,
        data["title"][:300],
        data["description"],
        data["difficulty"],
        data["category"],
        data["track"],
        "python",
        data["docker_image"],
        starter_key,
        tests_key,
        int(data["time_limit_mins"]),
        int(data["points"]),
        data["optimal_hint"],
        user_id,
    )

    logger.info("Created generated problem id=%s slug=%s", problem_id, slug)
    return {"problem_id": str(problem_id), "slug": slug}
