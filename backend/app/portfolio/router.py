"""
Portfolio card API — public read endpoints + authenticated refresh.
"""
import hashlib
import json
import logging

from fastapi import APIRouter, Depends, HTTPException

from app import db
from app.auth.dependencies import get_current_user
from app.portfolio.generator import generate_portfolio_card
from app.redis import get_redis

logger = logging.getLogger(__name__)
router = APIRouter(tags=["portfolio"])

_CACHE_TTL = 60  # seconds


# ── GET /portfolio/{github_login} — public ────────────────────────────────────

@router.get("/portfolio/{github_login}")
async def get_portfolio(github_login: str):
    user = await db.fetchrow(
        "SELECT * FROM users WHERE github_login = $1", github_login
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    redis = get_redis()
    cache_key = f"portfolio:{user['id']}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    card = await generate_portfolio_card(str(user["id"]))
    await redis.setex(cache_key, _CACHE_TTL, json.dumps(card))
    return card


# ── GET /portfolio/{github_login}/verify — public ─────────────────────────────

@router.get("/portfolio/{github_login}/verify")
async def verify_portfolio(github_login: str):
    user = await db.fetchrow(
        "SELECT * FROM users WHERE github_login = $1", github_login
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    card_row = await db.fetchrow(
        "SELECT * FROM portfolio_cards WHERE user_id = $1", user["id"]
    )

    if not card_row or not card_row["card_hash"] or not card_row["signature"]:
        return {
            "valid": False,
            "github_login": github_login,
            "signed_at": None,
            "issues_resolved": int(card_row["issues_resolved"]) if card_row else 0,
            "card_hash": None,
        }

    # Reconstruct card_data from stored columns (must match generator structure exactly)
    skill_radar = card_row["skill_radar"]
    if isinstance(skill_radar, str):
        skill_radar = json.loads(skill_radar)

    highlights = card_row["highlights"]
    if isinstance(highlights, str):
        highlights = json.loads(highlights)

    resolution_log = card_row["resolution_log"]
    if isinstance(resolution_log, str):
        resolution_log = json.loads(resolution_log)

    card_data = {
        "user": {
            "github_login": user["github_login"],
            "name": user["name"],
            "avatar_url": user["avatar_url"],
            "career_track": user["career_track"],
        },
        "issues_resolved": int(card_row["issues_resolved"]),
        "avg_score": float(card_row["avg_score"]),
        "skill_percentile": int(card_row["skill_percentile"]),
        "skill_radar": skill_radar,
        "highlights": highlights,
        "resolution_log": resolution_log,
    }

    canonical_json = json.dumps(card_data, sort_keys=True, ensure_ascii=False)
    expected_hash = "sha256:" + hashlib.sha256(canonical_json.encode()).hexdigest()
    is_valid = expected_hash == card_row["card_hash"]

    return {
        "valid": is_valid,
        "github_login": github_login,
        "signed_at": card_row["signed_at"].isoformat() if card_row["signed_at"] else None,
        "issues_resolved": int(card_row["issues_resolved"]),
        "card_hash": card_row["card_hash"],
    }


# ── POST /portfolio/refresh — requires auth ───────────────────────────────────

@router.post("/portfolio/refresh")
async def refresh_portfolio(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["id"])
    redis = get_redis()

    # Bust cache so the next GET re-generates
    await redis.delete(f"portfolio:{user_id}")

    card = await generate_portfolio_card(user_id)

    # Cache the fresh card
    await redis.setex(f"portfolio:{user_id}", _CACHE_TTL, json.dumps(card))
    return card
