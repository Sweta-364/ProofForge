"""
Problems API: serves the current problem for the authenticated user, including
the full starter codebase extracted from MinIO.
"""
import io
import logging
import tarfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app import db, minio as minio_module
from app.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["problems"])


@router.get("/problems/current")
async def get_current_problem(current_user: dict = Depends(get_current_user)):
    """
    Returns the active session + full problem (with starter files) for the user.

    Selection logic:
    1. Use an existing active session if one exists.
    2. Otherwise find the lowest display_order problem the user hasn't completed.
    3. Create a session (ON CONFLICT DO NOTHING handles a race condition).
    """
    user_id = str(current_user["id"])

    # -- Existing active session? ---------------------------------------------
    session = await db.fetchrow(
        """
        SELECT s.*, p.id AS prob_id
        FROM   active_sessions s
        JOIN   problems p ON p.id = s.problem_id
        WHERE  s.user_id = $1
          AND  s.status  = 'active'
        ORDER  BY s.started_at DESC
        LIMIT  1
        """,
        user_id,
    )

    if session:
        problem = await db.fetchrow(
            "SELECT * FROM problems WHERE id = $1", session["problem_id"]
        )
    else:
        # -- Find next unsolved problem ----------------------------------------
        problem = await db.fetchrow(
            """
            SELECT p.*
            FROM   problems p
            WHERE  p.is_active = TRUE
              AND  p.id NOT IN (
                       SELECT problem_id FROM submissions
                       WHERE  user_id = $1
                         AND  status  = 'completed'
                         AND  score  >= 60
                   )
            ORDER  BY p.display_order
            LIMIT  1
            """,
            user_id,
        )
        if not problem:
            raise HTTPException(
                status_code=404,
                detail="No more problems available — all solved!",
            )

        # Create session (UNIQUE constraint on user_id + problem_id)
        session_id = await db.fetchval(
            """
            INSERT INTO active_sessions (user_id, problem_id)
            VALUES ($1, $2)
            ON CONFLICT (user_id, problem_id) DO UPDATE
                SET last_saved_at = NOW()
            RETURNING id
            """,
            user_id,
            str(problem["id"]),
        )
        session = {"id": session_id}

    # -- Fetch starter files from MinIO ---------------------------------------
    files: dict[str, str] = {}
    try:
        tar_bytes = minio_module.download_file(
            minio_module.PROBLEMS_BUCKET, problem["codebase_key"]
        )
        files = _extract_tar_to_dict(tar_bytes)
    except Exception as e:
        logger.error(
            "Failed to download starter codebase for %s: %s",
            problem["slug"], e,
        )
        # Return empty files dict so the editor still opens
        files = {}

    return {
        "session_id": str(session["id"]),
        "problem": {
            "id": str(problem["id"]),
            "slug": problem["slug"],
            "title": problem["title"],
            "description": problem["description"],
            "difficulty": problem["difficulty"],
            "category": problem["category"],
            "language": problem["language"],
            "files": files,
        },
    }


def _extract_tar_to_dict(tar_bytes: bytes) -> dict[str, str]:
    """Extract .py files from a tar.gz blob → {relative_path: content}."""
    result: dict[str, str] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue
                if not member.name.endswith(".py"):
                    continue
                parts = Path(member.name).parts
                if "hidden" in parts or "__pycache__" in parts:
                    continue
                f = tar.extractfile(member)
                if f is None:
                    continue
                result[member.name] = f.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning("Tar extraction failed: %s", e)
    return result
