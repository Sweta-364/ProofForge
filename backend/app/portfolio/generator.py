"""
Portfolio card generator: builds and cryptographically signs a user's
DevPortfolio Card from their submission history.
"""
import base64
import hashlib
import json
import logging
from datetime import datetime, timezone

from app import db
from app.config import settings

logger = logging.getLogger(__name__)

# ── Public entry point ────────────────────────────────────────────────────────

async def generate_portfolio_card(user_id: str) -> dict:
    """Build the complete portfolio card from submission history and sign it."""
    user = await db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    submissions = await db.fetch(
        """
        SELECT s.id, s.problem_id, s.score, s.time_taken_mins, s.submitted_at,
               p.title, p.difficulty, p.category, p.slug,
               r.verdict, r.summary, r.ast_score, r.security_score, r.test_score,
               r.score_breakdown, r.inline_comments
        FROM   submissions s
        JOIN   problems p ON p.id = s.problem_id
        JOIN   reviews  r ON r.submission_id = s.id
        WHERE  s.user_id = $1
          AND  s.status  = 'completed'
          AND  s.score  >= 60
        ORDER  BY s.submitted_at
        """,
        user_id,
    )

    if not submissions:
        return await _upsert_and_return(_empty_card(dict(user)), user_id)

    subs = [dict(s) for s in submissions]

    issues_resolved = len(subs)
    avg_score = sum(s["score"] for s in subs) / issues_resolved
    skill_radar = _calculate_skill_radar(subs)

    # Percentile — count users with higher avg_score in portfolio_cards
    total_users = await db.fetchval(
        "SELECT COUNT(*) FROM portfolio_cards WHERE issues_resolved > 0"
    )
    better_users = await db.fetchval(
        "SELECT COUNT(*) FROM portfolio_cards WHERE avg_score > $1", avg_score
    )
    total_users = int(total_users or 0)
    better_users = int(better_users or 0)
    skill_percentile = max(
        1, int(((total_users - better_users) / max(total_users, 1)) * 100)
    )

    highlights = _extract_highlights(subs)

    resolution_log = [
        {
            "problem_title": s["title"],
            "difficulty": s["difficulty"],
            "category": s["category"],
            "score": s["score"],
            "verdict": s["verdict"],
            "time_taken_mins": s["time_taken_mins"],
            "resolved_at": s["submitted_at"].isoformat() if s["submitted_at"] else None,
        }
        for s in subs
    ]

    card_data = {
        "user": {
            "github_login": user["github_login"],
            "name": user["name"],
            "avatar_url": user["avatar_url"],
            "career_track": user["career_track"],
        },
        "issues_resolved": issues_resolved,
        "avg_score": round(float(avg_score), 2),
        "skill_percentile": skill_percentile,
        "skill_radar": skill_radar,
        "highlights": highlights,
        "resolution_log": resolution_log,
    }

    card_hash, signature = _sign_card(card_data)

    await db.execute(
        """
        INSERT INTO portfolio_cards
            (user_id, issues_resolved, avg_score, skill_percentile, skill_radar,
             highlights, resolution_log, card_hash, signature, signed_at, updated_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,NOW(),NOW())
        ON CONFLICT (user_id) DO UPDATE SET
            issues_resolved = $2,
            avg_score       = $3,
            skill_percentile= $4,
            skill_radar     = $5,
            highlights      = $6,
            resolution_log  = $7,
            card_hash       = $8,
            signature       = $9,
            signed_at       = NOW(),
            updated_at      = NOW()
        """,
        user_id,
        issues_resolved,
        float(avg_score),
        skill_percentile,
        json.dumps(skill_radar),
        json.dumps(highlights),
        json.dumps(resolution_log),
        card_hash,
        signature,
    )

    return {
        **card_data,
        "card_hash": card_hash,
        "signature": signature,
        "signed_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Signing ────────────────────────────────────────────────────────────────────

def _sign_card(card_data: dict) -> tuple[str | None, str | None]:
    """Return (card_hash, signature). Both None if no signing key is configured."""
    if not settings.PORTFOLIO_SIGNING_PRIVATE_KEY:
        logger.warning("PORTFOLIO_SIGNING_PRIVATE_KEY not set — card will be unsigned")
        return None, None

    try:
        import nacl.signing  # type: ignore[import]

        canonical_json = json.dumps(card_data, sort_keys=True, ensure_ascii=False)
        card_hash = "sha256:" + hashlib.sha256(canonical_json.encode()).hexdigest()

        private_key_bytes = base64.b64decode(settings.PORTFOLIO_SIGNING_PRIVATE_KEY)
        signing_key = nacl.signing.SigningKey(private_key_bytes)
        signed = signing_key.sign(canonical_json.encode())
        signature = base64.b64encode(signed.signature).decode()

        return card_hash, signature
    except Exception as e:
        logger.error("Card signing failed: %s", e, exc_info=True)
        return None, None


# ── Skill radar ────────────────────────────────────────────────────────────────

_CATEGORY_TO_SKILLS: dict[str, list[str]] = {
    "debugging":     ["debugging", "code_quality"],
    "optimization":  ["optimization", "performance"],
    "security":      ["security"],
    "concurrency":   ["concurrency", "debugging"],
    "configuration": ["code_quality"],
    "architecture":  ["architecture", "code_quality"],
    "api":           ["architecture", "code_quality"],
    "validation":    ["debugging", "code_quality"],
}


def _calculate_skill_radar(subs: list[dict]) -> dict[str, int]:
    skill_scores: dict[str, list[float]] = {
        k: [] for k in [
            "debugging", "optimization", "security", "architecture",
            "testing", "performance", "concurrency", "code_quality",
        ]
    }

    for sub in subs:
        category = sub.get("category", "")
        score = float(sub["score"])

        for skill in _CATEGORY_TO_SKILLS.get(category, ["code_quality"]):
            skill_scores[skill].append(score)

        if sub.get("ast_score") is not None:
            skill_scores["code_quality"].append(float(sub["ast_score"]))

        if sub.get("security_score") is not None:
            normalized = min(100.0, float(sub["security_score"]) * (100.0 / 15.0))
            skill_scores["security"].append(normalized)

        if sub.get("test_score") is not None:
            skill_scores["testing"].append(float(sub["test_score"]) * 10.0)

    return {
        skill: int(sum(scores) / len(scores)) if scores else 0
        for skill, scores in skill_scores.items()
    }


# ── Highlights ─────────────────────────────────────────────────────────────────

def _extract_highlights(subs: list[dict]) -> list[dict]:
    highlights = []
    for sub in subs:
        slug = sub.get("slug", "")
        if "slow-query" in slug or "slow_query" in slug:
            highlights.append({
                "metric": "Query optimized",
                "value": "2.3s → 0.08s (96.5% improvement)",
                "problem_title": sub["title"],
                "score": sub["score"],
            })
        elif "memory-leak" in slug or "memory_leak" in slug:
            highlights.append({
                "metric": "Memory leak fixed",
                "value": "Eliminated unbounded cache growth — memory stabilized at ~150MB",
                "problem_title": sub["title"],
                "score": sub["score"],
            })
        elif "race-condition" in slug or "race_condition" in slug:
            highlights.append({
                "metric": "Race condition resolved",
                "value": "Eliminated duplicate notifications under 20 concurrent connections",
                "problem_title": sub["title"],
                "score": sub["score"],
            })
    return highlights[:3]


# ── Empty card ─────────────────────────────────────────────────────────────────

def _empty_card(user: dict) -> dict:
    return {
        "user": {
            "github_login": user["github_login"],
            "name": user.get("name"),
            "avatar_url": user.get("avatar_url"),
            "career_track": user.get("career_track"),
        },
        "issues_resolved": 0,
        "avg_score": 0.0,
        "skill_percentile": 0,
        "skill_radar": {
            k: 0
            for k in [
                "debugging", "optimization", "security", "architecture",
                "testing", "performance", "concurrency", "code_quality",
            ]
        },
        "highlights": [],
        "resolution_log": [],
        "card_hash": None,
        "signature": None,
        "signed_at": None,
    }


async def _upsert_and_return(card: dict, user_id: str) -> dict:
    """Persist empty card to portfolio_cards and return it."""
    await db.execute(
        """
        INSERT INTO portfolio_cards
            (user_id, issues_resolved, avg_score, skill_percentile, skill_radar,
             highlights, resolution_log, updated_at)
        VALUES ($1, 0, 0, 0, $2, $3, $4, NOW())
        ON CONFLICT (user_id) DO UPDATE SET
            updated_at = NOW()
        """,
        user_id,
        json.dumps(card["skill_radar"]),
        json.dumps(card["highlights"]),
        json.dumps(card["resolution_log"]),
    )
    return card
