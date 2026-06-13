import logging
from datetime import date, timedelta

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
        SELECT p.id, p.slug, p.title, p.difficulty, p.category, p.track,
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
          AND  (p.owner_user_id IS NULL OR p.owner_user_id = $1::uuid)
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
                "track": r["track"],
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


@router.get("/users/me/activity")
async def get_activity(current_user: dict = Depends(get_current_user)):
    """Daily activity counts (last 366 days) + streaks for the profile heatmap.

    Activity = submissions made that day (any status) plus sessions started.
    """
    user_id = str(current_user["id"])

    rows = await db.fetch(
        """
        SELECT day, SUM(cnt)::int AS count FROM (
            SELECT DATE(submitted_at) AS day, COUNT(*) AS cnt
            FROM   submissions
            WHERE  user_id = $1
              AND  submitted_at >= NOW() - INTERVAL '366 days'
            GROUP  BY DATE(submitted_at)
            UNION ALL
            SELECT DATE(started_at) AS day, COUNT(*) AS cnt
            FROM   active_sessions
            WHERE  user_id = $1
              AND  started_at >= NOW() - INTERVAL '366 days'
            GROUP  BY DATE(started_at)
        ) activity
        GROUP  BY day
        ORDER  BY day
        """,
        user_id,
    )

    counts = {r["day"]: r["count"] for r in rows}

    # Streaks over all active days (consecutive calendar days)
    today = date.today()
    active_days = sorted(counts.keys())
    longest = current = 0
    prev: date | None = None
    for d in active_days:
        current = current + 1 if prev is not None and (d - prev).days == 1 else 1
        longest = max(longest, current)
        prev = d

    # Current streak must end today or yesterday
    current_streak = 0
    cursor = today if today in counts else today - timedelta(days=1)
    while cursor in counts:
        current_streak += 1
        cursor -= timedelta(days=1)

    return {
        "days": [
            {"date": d.isoformat(), "count": c} for d, c in sorted(counts.items())
        ],
        "total_active_days": len(active_days),
        "total_activity": sum(counts.values()),
        "current_streak": current_streak,
        "longest_streak": longest,
        "max_in_one_day": max(counts.values(), default=0),
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
