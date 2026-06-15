"""
Community API: posts (doubts) with optional image, text answers, up/down voting,
and user search. Usernames are the GitHub login stored on the users table.

Images are stored in MinIO and served back through GET .../image — never via
presigned URLs, because the MinIO endpoint host is not reachable from the browser.
"""
import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import Response

from app import db, minio as minio_module
from app.auth.dependencies import get_current_user
from app.community.schemas import CreatePostRequest, CreateAnswerRequest, VoteRequest

logger = logging.getLogger(__name__)
router = APIRouter(tags=["community"])

_MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
_IMAGE_KEY_PREFIX = "posts/"


# ── helpers ──────────────────────────────────────────────────────────────────

def _parse_uuid(value: str, label: str = "resource") -> str:
    """Validate a path param is a real UUID; 404 otherwise (no DB round-trip)."""
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=404, detail=f"{label} not found")


def _post_to_dict(row) -> dict:
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "body": row["body"],
        "has_image": row["image_key"] is not None,
        "score": row["score"],
        "my_vote": row["my_vote"],
        "answer_count": row["answer_count"],
        "created_at": row["created_at"].isoformat(),
        "author": {
            "github_login": row["github_login"],
            "name": row["name"],
            "avatar_url": row["avatar_url"],
        },
    }


def _answer_to_dict(row) -> dict:
    return {
        "id": str(row["id"]),
        "body": row["body"],
        "score": row["score"],
        "my_vote": row["my_vote"],
        "created_at": row["created_at"].isoformat(),
        "author": {
            "github_login": row["github_login"],
            "name": row["name"],
            "avatar_url": row["avatar_url"],
        },
    }


async def _fetch_post_row(post_id: str, user_id):
    """Single post with author, answer count, and the caller's vote (or None)."""
    return await db.fetchrow(
        """
        SELECT p.id, p.title, p.body, p.image_key, p.score, p.created_at,
               u.github_login, u.name, u.avatar_url,
               (SELECT COUNT(*) FROM community_answers a WHERE a.post_id = p.id) AS answer_count,
               COALESCE(v.value, 0) AS my_vote
        FROM community_posts p
        JOIN users u ON u.id = p.user_id
        LEFT JOIN community_votes v
               ON v.target_type = 'post' AND v.target_id = p.id AND v.user_id = $2
        WHERE p.id = $1
        """,
        post_id, user_id,
    )


async def _apply_vote(
    user_id, target_type: str, target_id: str, value: int, counter_table: str
) -> dict:
    """Upsert/remove a vote and resync the target's denormalized score counter."""
    if value == 0:
        await db.execute(
            "DELETE FROM community_votes WHERE user_id=$1 AND target_type=$2 AND target_id=$3",
            user_id, target_type, target_id,
        )
    else:
        await db.execute(
            """INSERT INTO community_votes (user_id, target_type, target_id, value)
               VALUES ($1, $2, $3, $4)
               ON CONFLICT (user_id, target_type, target_id)
               DO UPDATE SET value = EXCLUDED.value""",
            user_id, target_type, target_id, value,
        )

    new_score = await db.fetchval(
        "SELECT COALESCE(SUM(value), 0) FROM community_votes WHERE target_type=$1 AND target_id=$2",
        target_type, target_id,
    )
    # counter_table is an internal constant ('community_posts'/'community_answers'),
    # never user input — safe to interpolate.
    await db.execute(
        f"UPDATE {counter_table} SET score=$1 WHERE id=$2", int(new_score), target_id
    )
    return {"score": int(new_score), "my_vote": value}


# ── Posts feed ───────────────────────────────────────────────────────────────

@router.get("/community/posts")
async def list_posts(
    sort: str = Query("new", pattern="^(new|top)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    order_by = (
        "p.score DESC, p.created_at DESC" if sort == "top" else "p.created_at DESC"
    )
    offset = (page - 1) * limit
    rows = await db.fetch(
        f"""
        SELECT p.id, p.title, p.body, p.image_key, p.score, p.created_at,
               u.github_login, u.name, u.avatar_url,
               (SELECT COUNT(*) FROM community_answers a WHERE a.post_id = p.id) AS answer_count,
               COALESCE(v.value, 0) AS my_vote
        FROM community_posts p
        JOIN users u ON u.id = p.user_id
        LEFT JOIN community_votes v
               ON v.target_type = 'post' AND v.target_id = p.id AND v.user_id = $1
        ORDER BY {order_by}
        LIMIT $2 OFFSET $3
        """,
        current_user["id"], limit, offset,
    )
    return {"posts": [_post_to_dict(r) for r in rows], "page": page, "limit": limit}


@router.post("/community/posts/image", status_code=201)
async def upload_post_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Only image files are allowed")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (max 5 MB)")

    key = f"{_IMAGE_KEY_PREFIX}{uuid.uuid4().hex}"
    await asyncio.to_thread(
        minio_module.upload_bytes,
        minio_module.COMMUNITY_BUCKET, key, data, content_type,
    )
    return {"image_key": key, "image_type": content_type}


@router.post("/community/posts", status_code=201)
async def create_post(
    body: CreatePostRequest,
    current_user: dict = Depends(get_current_user),
):
    image_key = body.image_key
    image_type = body.image_type
    if image_key and not image_key.startswith(_IMAGE_KEY_PREFIX):
        raise HTTPException(status_code=400, detail="Invalid image reference")

    post_id = await db.fetchval(
        """INSERT INTO community_posts (user_id, title, body, image_key, image_type)
           VALUES ($1, $2, $3, $4, $5)
           RETURNING id""",
        current_user["id"], body.title, body.body, image_key, image_type,
    )
    row = await _fetch_post_row(str(post_id), current_user["id"])
    return _post_to_dict(row)


@router.get("/community/posts/{post_id}")
async def get_post(
    post_id: str,
    current_user: dict = Depends(get_current_user),
):
    pid = _parse_uuid(post_id, "Post")
    post = await _fetch_post_row(pid, current_user["id"])
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    answers = await db.fetch(
        """
        SELECT a.id, a.body, a.score, a.created_at,
               u.github_login, u.name, u.avatar_url,
               COALESCE(v.value, 0) AS my_vote
        FROM community_answers a
        JOIN users u ON u.id = a.user_id
        LEFT JOIN community_votes v
               ON v.target_type = 'answer' AND v.target_id = a.id AND v.user_id = $2
        WHERE a.post_id = $1
        ORDER BY a.score DESC, a.created_at ASC
        """,
        pid, current_user["id"],
    )
    return {
        "post": _post_to_dict(post),
        "answers": [_answer_to_dict(a) for a in answers],
    }


@router.get("/community/posts/{post_id}/image")
async def get_post_image(post_id: str):
    # Public (no auth): an <img> tag cannot send an Authorization header. Post IDs
    # are unguessable UUIDs and images are non-sensitive community content.
    pid = _parse_uuid(post_id, "Post")
    row = await db.fetchrow(
        "SELECT image_key, image_type FROM community_posts WHERE id=$1", pid
    )
    if not row or not row["image_key"]:
        raise HTTPException(status_code=404, detail="Image not found")
    try:
        data = await asyncio.to_thread(
            minio_module.download_file, minio_module.COMMUNITY_BUCKET, row["image_key"]
        )
    except Exception as e:
        logger.warning("Failed to load community image %s: %s", row["image_key"], e)
        raise HTTPException(status_code=404, detail="Image not found")
    return Response(
        content=data,
        media_type=row["image_type"] or "application/octet-stream",
        headers={"Cache-Control": "public, max-age=86400"},
    )


# ── Answers ──────────────────────────────────────────────────────────────────

@router.post("/community/posts/{post_id}/answers", status_code=201)
async def create_answer(
    post_id: str,
    body: CreateAnswerRequest,
    current_user: dict = Depends(get_current_user),
):
    pid = _parse_uuid(post_id, "Post")
    exists = await db.fetchval("SELECT 1 FROM community_posts WHERE id=$1", pid)
    if not exists:
        raise HTTPException(status_code=404, detail="Post not found")

    answer_id = await db.fetchval(
        """INSERT INTO community_answers (post_id, user_id, body)
           VALUES ($1, $2, $3)
           RETURNING id""",
        pid, current_user["id"], body.body,
    )
    row = await db.fetchrow(
        """
        SELECT a.id, a.body, a.score, a.created_at,
               u.github_login, u.name, u.avatar_url, 0 AS my_vote
        FROM community_answers a
        JOIN users u ON u.id = a.user_id
        WHERE a.id = $1
        """,
        answer_id,
    )
    return _answer_to_dict(row)


# ── Voting ───────────────────────────────────────────────────────────────────

@router.post("/community/posts/{post_id}/vote")
async def vote_post(
    post_id: str,
    body: VoteRequest,
    current_user: dict = Depends(get_current_user),
):
    pid = _parse_uuid(post_id, "Post")
    if not await db.fetchval("SELECT 1 FROM community_posts WHERE id=$1", pid):
        raise HTTPException(status_code=404, detail="Post not found")
    return await _apply_vote(current_user["id"], "post", pid, body.value, "community_posts")


@router.post("/community/answers/{answer_id}/vote")
async def vote_answer(
    answer_id: str,
    body: VoteRequest,
    current_user: dict = Depends(get_current_user),
):
    aid = _parse_uuid(answer_id, "Answer")
    if not await db.fetchval("SELECT 1 FROM community_answers WHERE id=$1", aid):
        raise HTTPException(status_code=404, detail="Answer not found")
    return await _apply_vote(current_user["id"], "answer", aid, body.value, "community_answers")


# ── User search ──────────────────────────────────────────────────────────────

@router.get("/community/users/search")
async def search_users(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(20, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    pattern = f"%{q}%"
    rows = await db.fetch(
        """
        SELECT github_login, name, avatar_url, total_score, issues_resolved
        FROM users
        WHERE github_login ILIKE $1 OR name ILIKE $1
        ORDER BY total_score DESC, github_login ASC
        LIMIT $2
        """,
        pattern, limit,
    )
    return {
        "users": [
            {
                "github_login": r["github_login"],
                "name": r["name"],
                "avatar_url": r["avatar_url"],
                "total_score": r["total_score"],
                "issues_resolved": r["issues_resolved"],
            }
            for r in rows
        ]
    }
