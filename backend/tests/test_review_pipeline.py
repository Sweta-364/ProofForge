"""
Tests for the AI review pipeline: AST analysis, security scan, Claude review.
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.config import settings
from app.submissions.review_pipeline import ReviewPipeline


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def pipeline():
    return ReviewPipeline()


@pytest.fixture(autouse=True)
def force_anthropic_provider(monkeypatch):
    """These tests mock the Anthropic client, so pin the provider regardless of
    what the local .env sets (dev machines may use REVIEW_PROVIDER=mock)."""
    monkeypatch.setattr(settings, "REVIEW_PROVIDER", "anthropic")


MEMORY_LEAK_STARTER = {
    "starter/auth.py": """\
import jwt

SECRET_KEY = "test-secret"
_token_cache: dict = {}

async def verify_token(token: str):
    if token in _token_cache:
        return _token_cache[token]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        _token_cache[token] = payload
        return payload
    except Exception:
        return None

def get_cache_size() -> int:
    return len(_token_cache)
"""
}

CLEAN_CODE = {
    "starter/auth.py": """\
import cachetools
import asyncio

SECRET_KEY = "test-secret"
_token_cache = cachetools.TTLCache(maxsize=1000, ttl=300)
_lock = asyncio.Lock()

async def verify_token(token: str):
    async with _lock:
        if token in _token_cache:
            return _token_cache[token]
    return None
"""
}

MOCK_REVIEW_JSON = {
    "verdict": "accept",
    "overall_score": 88,
    "score_breakdown": {
        "correctness": 28,
        "code_quality": 20,
        "performance": 18,
        "security": 12,
        "tests": 10,
    },
    "summary": "Good fix. The TTLCache prevents unbounded growth. Consider using asyncio.Lock consistently.",
    "inline_comments": [
        {
            "file": "starter/auth.py",
            "line": 5,
            "severity": "praise",
            "comment": "Using TTLCache from cachetools is exactly the right approach here. It evicts by both size and time, preventing memory leaks.",
        }
    ],
    "learning_resources": [
        {
            "title": "cachetools documentation",
            "url": "https://cachetools.readthedocs.io/",
            "why": "Direct reference for the TTLCache used in the fix.",
        }
    ],
    "architectural_note": None,
}


# ── AST analysis tests ────────────────────────────────────────────────────────

async def test_ast_detects_global_mutable(pipeline: ReviewPipeline):
    """AST analysis on the memory-leak starter must find global_mutable_state."""
    result = await pipeline.run_ast_analysis(MEMORY_LEAK_STARTER)
    assert len(result["anti_patterns"]) >= 1
    assert any("global_mutable_state" in p for p in result["anti_patterns"])


async def test_ast_clean_code(pipeline: ReviewPipeline):
    """Clean fixed code with no top-level mutable containers must have no anti-patterns."""
    result = await pipeline.run_ast_analysis(CLEAN_CODE)
    assert result["anti_patterns"] == [], (
        f"Expected no anti-patterns, got: {result['anti_patterns']}"
    )


async def test_ast_returns_required_keys(pipeline: ReviewPipeline):
    """run_ast_analysis must always return all expected keys."""
    result = await pipeline.run_ast_analysis({"starter/main.py": "x = 1\n"})
    for key in ("anti_patterns", "max_complexity", "max_nesting", "overall_ast_score"):
        assert key in result, f"Missing key: {key}"


async def test_ast_ignores_non_python(pipeline: ReviewPipeline):
    """Non-.py files are skipped; result should still be a valid dict."""
    result = await pipeline.run_ast_analysis({"README.md": "# hello\n"})
    assert result["overall_ast_score"] == 100
    assert result["anti_patterns"] == []


# ── Security scan tests ───────────────────────────────────────────────────────

async def test_security_scan_runs(pipeline: ReviewPipeline, tmp_path: Path):
    """run_security_scan must return a dict with 'findings' and 'security_score'."""
    py_file = tmp_path / "test_code.py"
    py_file.write_text("import os\nos.system('ls')\n")
    result = await pipeline.run_security_scan(tmp_path)
    assert "findings" in result
    assert "security_score" in result
    assert isinstance(result["security_score"], int)
    assert 0 <= result["security_score"] <= 15


async def test_security_scan_clean_code(pipeline: ReviewPipeline, tmp_path: Path):
    """Clean code should return security_score == 15 (no deductions)."""
    py_file = tmp_path / "clean.py"
    py_file.write_text("def add(a, b):\n    return a + b\n")
    result = await pipeline.run_security_scan(tmp_path)
    assert result["security_score"] == 15


# ── Claude review tests ───────────────────────────────────────────────────────

async def test_claude_review_returns_valid_json(pipeline: ReviewPipeline):
    """With a mocked Anthropic client, call_claude_review must return a parsed dict."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps(MOCK_REVIEW_JSON))]

    with patch.object(pipeline.anthropic_client.messages, "create", return_value=mock_response):
        result = await pipeline.call_claude_review(
            problem_meta={
                "title": "Memory Leak Fix",
                "difficulty": "mid",
                "description": "Fix the unbounded token cache.",
                "optimal_hint": "Use TTLCache",
            },
            code_files=CLEAN_CODE,
            test_results={"total": 5, "passed": 5, "failed": 0, "status": "completed", "tests": []},
            ast_output={"anti_patterns": [], "max_complexity": 3, "max_nesting": 2, "overall_ast_score": 100},
            security_output={"findings": [], "security_score": 15},
            original_files=MEMORY_LEAK_STARTER,
        )

    assert result["verdict"] == "accept"
    assert result["overall_score"] == 88
    assert "score_breakdown" in result
    assert "inline_comments" in result
    assert "learning_resources" in result
    assert "error" not in result


async def test_claude_review_bad_json_handled(pipeline: ReviewPipeline):
    """If Claude returns invalid JSON, result must be an error dict — no exception raised."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="This is not JSON at all!!!")]

    with patch.object(pipeline.anthropic_client.messages, "create", return_value=mock_response):
        result = await pipeline.call_claude_review(
            problem_meta={
                "title": "Test",
                "difficulty": "junior",
                "description": "desc",
                "optimal_hint": None,
            },
            code_files={"starter/main.py": "pass\n"},
            test_results={"total": 0, "passed": 0, "failed": 0, "status": "completed", "tests": []},
            ast_output={"anti_patterns": [], "max_complexity": 1, "max_nesting": 0, "overall_ast_score": 100},
            security_output={"findings": [], "security_score": 15},
            original_files={},
        )

    assert "error" in result
    assert result["error"] == "review_parse_failed"


async def test_claude_review_missing_field_handled(pipeline: ReviewPipeline):
    """If Claude returns JSON missing required fields, result must be an error dict."""
    incomplete = {"verdict": "accept"}  # missing overall_score, etc.
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps(incomplete))]

    with patch.object(pipeline.anthropic_client.messages, "create", return_value=mock_response):
        result = await pipeline.call_claude_review(
            problem_meta={"title": "T", "difficulty": "junior", "description": "", "optimal_hint": None},
            code_files={},
            test_results={"total": 0, "passed": 0, "failed": 0, "status": "completed", "tests": []},
            ast_output={"anti_patterns": [], "max_complexity": 1, "max_nesting": 0, "overall_ast_score": 100},
            security_output={"findings": [], "security_score": 15},
            original_files={},
        )

    assert "error" in result
