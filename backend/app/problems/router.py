"""
Problems API: lists the problem bank and serves individual problems (with the
full starter codebase extracted from MinIO) for the authenticated user.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException

from app import db, minio as minio_module
from app.auth.dependencies import get_current_user
from app.tar_utils import extract_tar_to_dict

logger = logging.getLogger(__name__)
router = APIRouter(tags=["problems"])


@router.get("/problems")
async def list_problems(current_user: dict = Depends(get_current_user)):
    """All active problems grouped data for the dashboard, with per-user progress."""
    user_id = str(current_user["id"])
    rows = await db.fetch(
        """
        SELECT p.id, p.slug, p.title, p.difficulty, p.category, p.track,
               p.language, p.time_limit_mins, p.points, p.display_order,
               MAX(s.score) FILTER (WHERE s.status = 'completed')   AS best_score,
               COUNT(s.id)                                          AS attempts,
               COALESCE(
                   BOOL_OR(s.status = 'completed' AND s.score >= 60),
                   FALSE
               )                                                    AS solved
        FROM   problems p
        LEFT   JOIN submissions s
               ON s.problem_id = p.id AND s.user_id = $1
        WHERE  p.is_active = TRUE
        GROUP  BY p.id
        ORDER  BY p.display_order
        """,
        user_id,
    )
    return {
        "problems": [
            {
                "id": str(r["id"]),
                "slug": r["slug"],
                "title": r["title"],
                "difficulty": r["difficulty"],
                "category": r["category"],
                "track": r["track"],
                "language": r["language"],
                "points": r["points"],
                "time_limit_mins": r["time_limit_mins"],
                "solved": r["solved"],
                "best_score": r["best_score"],
                "attempts": r["attempts"],
            }
            for r in rows
        ]
    }


@router.get("/problems/current")
async def get_current_problem(current_user: dict = Depends(get_current_user)):
    """
    Returns the active session + full problem (with starter files) for the user.

    Selection logic:
    1. Use an existing active session if one exists.
    2. Otherwise find the lowest display_order problem the user hasn't completed.
    """
    user_id = str(current_user["id"])

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
        return _problem_response(str(session["id"]), problem)

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

    session_id = await _open_session(user_id, str(problem["id"]))
    return _problem_response(session_id, problem)


@router.get("/problems/{slug}")
async def get_problem_by_slug(
    slug: str,
    current_user: dict = Depends(get_current_user),
):
    """Open (or resume) a session for a specific problem chosen by the user."""
    user_id = str(current_user["id"])

    problem = await db.fetchrow(
        "SELECT * FROM problems WHERE slug = $1 AND is_active = TRUE", slug
    )
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    session_id = await _open_session(user_id, str(problem["id"]))
    return _problem_response(session_id, problem)


async def _open_session(user_id: str, problem_id: str) -> str:
    """Create or resume the user's session for a problem."""
    session_id = await db.fetchval(
        """
        INSERT INTO active_sessions (user_id, problem_id)
        VALUES ($1, $2)
        ON CONFLICT (user_id, problem_id) DO UPDATE
            SET last_saved_at = NOW(), status = 'active'
        RETURNING id
        """,
        user_id,
        problem_id,
    )
    return str(session_id)


def _problem_response(session_id: str, problem) -> dict:
    files: dict[str, str] = {}
    try:
        tar_bytes = minio_module.download_file(
            minio_module.PROBLEMS_BUCKET, problem["codebase_key"]
        )
        files = extract_tar_to_dict(tar_bytes)
    except Exception as e:
        logger.error(
            "Failed to download starter codebase for %s: %s",
            problem["slug"], e,
        )
        # Return empty files dict so the editor still opens
        files = {}

    return {
        "session_id": session_id,
        "problem": {
            "id": str(problem["id"]),
            "slug": problem["slug"],
            "title": problem["title"],
            "description": problem["description"],
            "difficulty": problem["difficulty"],
            "category": problem["category"],
            "track": problem["track"],
            "language": problem["language"],
            "files": files,
        },
    }
