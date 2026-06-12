"""
Submission API: run-tests endpoint, submit endpoint, result/review retrieval.
The submission pipeline is a background asyncio task that streams progress via
Redis pub/sub → WebSocket.
"""
import asyncio
import io
import json
import logging
import shutil
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import db, minio as minio_module
from app.auth.dependencies import get_current_user
from app.config import settings
from app.redis import get_redis
from sandbox.runner import sandbox_runner
from app.submissions.review_pipeline import review_pipeline
from app.portfolio.generator import generate_portfolio_card

logger = logging.getLogger(__name__)
router = APIRouter(tags=["submissions"])


# ── Request models ─────────────────────────────────────────────────────────────

class RunTestsRequest(BaseModel):
    files: dict[str, str]


class SubmitRequest(BaseModel):
    session_id: str
    files: dict[str, str]


# ── Run-tests (synchronous — waits for container) ─────────────────────────────

@router.post("/sessions/{session_id}/run-tests")
async def run_tests(
    session_id: str,
    body: RunTestsRequest,
    current_user: dict = Depends(get_current_user),
):
    # Verify session belongs to caller
    session = await db.fetchrow(
        "SELECT * FROM active_sessions WHERE id=$1 AND user_id=$2",
        session_id, current_user["id"],
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    problem = await db.fetchrow(
        "SELECT * FROM problems WHERE id=$1", session["problem_id"]
    )
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    # Rate limit: max 10 test runs per session
    redis = get_redis()
    rate_key = f"ratelimit:runtests:{session_id}"
    count = await redis.incr(rate_key)
    if count == 1:
        await redis.expire(rate_key, 86400)  # 24-hour window
    if count > 10:
        raise HTTPException(
            status_code=429,
            detail="Maximum test runs reached for this session",
        )

    results = await sandbox_runner.run_tests(
        problem_slug=problem["slug"],
        code_files=body.files,
        test_suite="visible",
        problem_meta=dict(problem),
    )
    return results


# ── Submit (async — returns 202 immediately) ──────────────────────────────────

@router.post("/submissions", status_code=202)
async def submit(
    body: SubmitRequest,
    current_user: dict = Depends(get_current_user),
):
    session = await db.fetchrow(
        "SELECT * FROM active_sessions WHERE id=$1 AND user_id=$2",
        body.session_id, current_user["id"],
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    problem = await db.fetchrow(
        "SELECT * FROM problems WHERE id=$1", session["problem_id"]
    )
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    attempt = await db.fetchval(
        "SELECT COUNT(*) FROM submissions WHERE user_id=$1 AND problem_id=$2",
        current_user["id"], problem["id"],
    )

    submission_id = await db.fetchval(
        """INSERT INTO submissions
               (user_id, problem_id, session_id, status, code_snapshot, attempt_number)
           VALUES ($1, $2, $3, 'queued', $4, $5)
           RETURNING id""",
        current_user["id"],
        problem["id"],
        body.session_id,
        json.dumps(body.files),
        int(attempt) + 1,
    )

    asyncio.create_task(
        _process_submission(
            str(submission_id),
            body.files,
            body.session_id,
            str(current_user["id"]),
        )
    )

    return {"submission_id": str(submission_id), "status": "queued"}


# ── Status / review retrieval ─────────────────────────────────────────────────

@router.get("/submissions/{submission_id}")
async def get_submission(
    submission_id: str,
    current_user: dict = Depends(get_current_user),
):
    row = await db.fetchrow(
        "SELECT * FROM submissions WHERE id=$1 AND user_id=$2",
        submission_id, current_user["id"],
    )
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")
    return {
        "submission_id": str(row["id"]),
        "status": row["status"],
        "score": row["score"],
        "review_id": str(row["review_id"]) if row["review_id"] else None,
        "submitted_at": row["submitted_at"].isoformat(),
        "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
    }


@router.get("/submissions/{submission_id}/review")
async def get_review(
    submission_id: str,
    current_user: dict = Depends(get_current_user),
):
    sub = await db.fetchrow(
        "SELECT * FROM submissions WHERE id=$1 AND user_id=$2",
        submission_id, current_user["id"],
    )
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    if not sub["review_id"]:
        raise HTTPException(status_code=404, detail="Review not yet available")

    review = await db.fetchrow(
        "SELECT * FROM reviews WHERE id=$1", sub["review_id"]
    )
    if not review:
        raise HTTPException(status_code=404, detail="Review record missing")

    return {
        "verdict": review["verdict"],
        "overall_score": review["overall_score"],
        "score_breakdown": json.loads(review["score_breakdown"]),
        "summary": review["summary"],
        "inline_comments": json.loads(review["inline_comments"]),
        "learning_resources": (
            json.loads(review["learning_resources"])
            if review["learning_resources"]
            else []
        ),
        "architectural_note": review["architectural_note"],
        "code_snapshot": json.loads(sub["code_snapshot"]),
        "ast_score": review["ast_score"],
        "security_score": review["security_score"],
        "test_score": review["test_score"],
        "pipeline_duration_ms": review["pipeline_duration_ms"],
    }


# ── Background pipeline ────────────────────────────────────────────────────────

async def _process_submission(
    submission_id: str,
    files: dict[str, str],
    session_id: str,
    user_id: str,
) -> None:
    redis = get_redis()
    channel = f"submission:{submission_id}"

    async def notify(status: str, message: str) -> None:
        await redis.publish(
            channel,
            json.dumps({
                "type": "status_update",
                "status": status,
                "message": message,
                "submission_id": submission_id,
            }),
        )

    try:
        submission = await db.fetchrow(
            "SELECT * FROM submissions WHERE id=$1", submission_id
        )
        problem = await db.fetchrow(
            "SELECT * FROM problems WHERE id=$1", submission["problem_id"]
        )
        problem_meta = dict(problem)

        # Fetch original starter files for diff generation
        starter_bytes = minio_module.download_file(
            minio_module.PROBLEMS_BUCKET, problem["codebase_key"]
        )
        original_files = _extract_tar_to_dict(starter_bytes)

        # Stage A: run all tests
        await notify("running_tests", "Running test suite...")
        await db.execute(
            "UPDATE submissions SET status='running_tests' WHERE id=$1", submission_id
        )
        test_results = await sandbox_runner.run_tests(
            problem["slug"], files, test_suite="all", problem_meta=problem_meta
        )

        # Stage B+C: AST + security in parallel
        await notify("analyzing", "Analyzing code structure and security...")
        await db.execute(
            "UPDATE submissions SET status='analyzing' WHERE id=$1", submission_id
        )

        analysis_dir = Path(settings.SANDBOX_TEMP_DIR) / f"analysis_{submission_id}"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        for filepath, content in files.items():
            dest = analysis_dir / filepath
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

        ast_task = asyncio.create_task(review_pipeline.run_ast_analysis(files))
        security_task = asyncio.create_task(
            review_pipeline.run_security_scan(analysis_dir)
        )
        ast_output, security_output = await asyncio.gather(ast_task, security_task)
        shutil.rmtree(analysis_dir, ignore_errors=True)

        # Stage E: Claude review
        await notify("reviewing", "Generating AI code review...")
        await db.execute(
            "UPDATE submissions SET status='reviewing' WHERE id=$1", submission_id
        )

        start_time = time.time()
        review_data = await review_pipeline.call_claude_review(
            problem_meta, files, test_results,
            ast_output, security_output, original_files,
        )
        pipeline_ms = int((time.time() - start_time) * 1000)

        # Stage F: score + persist
        overall_score = review_data.get("overall_score", 0)
        if "error" in review_data:
            overall_score = _calculate_fallback_score(
                test_results, ast_output, security_output
            )

        review_id = await db.fetchval(
            """INSERT INTO reviews (
                   submission_id, verdict, overall_score, score_breakdown,
                   summary, inline_comments, learning_resources, architectural_note,
                   ast_score, security_score, test_score,
                   ast_output, security_output, test_output,
                   llm_raw, pipeline_duration_ms
               ) VALUES (
                   $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16
               ) RETURNING id""",
            submission_id,
            review_data.get("verdict", "major_revisions"),
            overall_score,
            json.dumps(review_data.get("score_breakdown", {})),
            review_data.get("summary", "Review processing failed"),
            json.dumps(review_data.get("inline_comments", [])),
            json.dumps(review_data.get("learning_resources", [])),
            review_data.get("architectural_note"),
            ast_output["overall_ast_score"],
            security_output["security_score"],
            _calc_test_score(test_results),
            json.dumps(ast_output),
            json.dumps(security_output),
            json.dumps(test_results),
            json.dumps(review_data)[:5000],
            pipeline_ms,
        )

        time_taken = None
        session_row = await db.fetchrow(
            "SELECT started_at FROM active_sessions WHERE id=$1", session_id
        )
        if session_row:
            time_taken = int(
                (datetime.now(timezone.utc) - session_row["started_at"]).total_seconds() / 60
            )

        await db.execute(
            """UPDATE submissions
               SET status='completed', score=$1, review_id=$2,
                   completed_at=NOW(), time_taken_mins=$3
               WHERE id=$4""",
            overall_score, review_id, time_taken, submission_id,
        )

        if overall_score >= 60:
            await db.execute(
                """UPDATE users
                   SET issues_resolved = issues_resolved + 1,
                       total_score     = total_score + $1,
                       last_active_at  = NOW()
                   WHERE id = $2""",
                overall_score, user_id,
            )
            asyncio.create_task(generate_portfolio_card(user_id))

        await redis.publish(
            channel,
            json.dumps({
                "type": "review_complete",
                "submission_id": submission_id,
                "score": overall_score,
                "verdict": review_data.get("verdict", "major_revisions"),
                "review_id": str(review_id),
            }),
        )

    except Exception as e:
        logger.error(
            "Submission pipeline failed for %s: %s", submission_id, e, exc_info=True
        )
        try:
            await db.execute(
                "UPDATE submissions SET status='failed' WHERE id=$1", submission_id
            )
        except Exception:
            pass
        try:
            await redis.publish(
                channel,
                json.dumps({
                    "type": "error",
                    "submission_id": submission_id,
                    "message": "Processing failed. Please try again.",
                    "code": "pipeline_error",
                }),
            )
        except Exception:
            pass


# ── Helper functions ───────────────────────────────────────────────────────────

def _extract_tar_to_dict(tar_bytes: bytes) -> dict[str, str]:
    """Extract a tar.gz bytes blob → {relative_path: file_content} for .py files only."""
    result: dict[str, str] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tar:
            count = 0
            for member in tar.getmembers():
                if count >= 50:
                    break
                if not member.isfile():
                    continue
                if not member.name.endswith(".py"):
                    continue
                # Skip hidden test directory
                parts = Path(member.name).parts
                if "hidden" in parts:
                    continue
                f = tar.extractfile(member)
                if f is None:
                    continue
                result[member.name] = f.read().decode("utf-8", errors="replace")
                count += 1
    except Exception as e:
        logger.warning("Failed to extract tar: %s", e)
    return result


def _calculate_fallback_score(
    test_results: dict, ast_output: dict, security_output: dict
) -> int:
    """Score when Claude API is unavailable."""
    total = test_results.get("total", 1) or 1
    passed = test_results.get("passed", 0)
    test_component = int((passed / total) * 30)
    ast_component = ast_output.get("overall_ast_score", 100) // 4
    sec_component = security_output.get("security_score", 15)
    return min(100, test_component + ast_component + sec_component)


def _calc_test_score(test_results: dict) -> int:
    """0–10 based on pass ratio."""
    total = test_results.get("total", 0)
    if total == 0:
        return 0
    passed = test_results.get("passed", 0)
    return round((passed / total) * 10)
