import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import db
from app.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["users"])

_VALID_TRACKS = {"fullstack", "backend", "frontend", "devops"}


class TrackUpdate(BaseModel):
    track: str


@router.get("/users/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.get("/users/me/progress")
async def get_progress(current_user: dict = Depends(get_current_user)):
    """Per-problem progress + recent submissions for the dashboard."""
    user_id = str(current_user["id"])

    problem_rows = await db.fetch(
        """
        SELECT p.id, p.slug, p.title, p.difficulty, p.category,
               p.points, p.display_order,
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

    submission_rows = await db.fetch(
        """
        SELECT s.id, s.status, s.score, s.submitted_at, s.completed_at,
               p.title AS problem_title, p.difficulty
        FROM   submissions s
        JOIN   problems p ON p.id = s.problem_id
        WHERE  s.user_id = $1
        ORDER  BY s.submitted_at DESC
        LIMIT  10
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
                "points": r["points"],
                "solved": r["solved"],
                "best_score": r["best_score"],
                "attempts": r["attempts"],
            }
            for r in problem_rows
        ],
        "recent_submissions": [
            {
                "id": str(r["id"]),
                "problem_title": r["problem_title"],
                "difficulty": r["difficulty"],
                "status": r["status"],
                "score": r["score"],
                "submitted_at": r["submitted_at"].isoformat(),
                "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
            }
            for r in submission_rows
        ],
    }


@router.put("/users/me/track")
async def update_track(
    body: TrackUpdate,
    current_user: dict = Depends(get_current_user),
):
    if body.track not in _VALID_TRACKS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid track. Must be one of: {', '.join(sorted(_VALID_TRACKS))}",
        )
    user = await db.fetchrow(
        """
        UPDATE users
        SET career_track = $1, current_difficulty = 'junior'
        WHERE id = $2
        RETURNING id, github_login, name, email, avatar_url, career_track,
                  current_difficulty, total_score, issues_resolved, created_at
        """,
        body.track,
        str(current_user["id"]),
    )
    return dict(user)
