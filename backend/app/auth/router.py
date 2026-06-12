import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from jose import jwt, JWTError

from app import db, redis as redis_module
from app.auth.dependencies import get_current_user, oauth2_scheme
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])


@router.get("/auth/github")
async def github_login():
    state = secrets.token_hex(32)
    r = redis_module.get_redis()
    await r.setex(f"oauth_state:{state}", 300, "1")
    url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        "&scope=read:user,user:email"
        f"&state={state}"
    )
    return RedirectResponse(url=url, status_code=302)


@router.get("/auth/callback")
async def github_callback(code: str, state: str):
    r = redis_module.get_redis()
    if not await r.get(f"oauth_state:{state}"):
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")
    await r.delete(f"oauth_state:{state}")

    async with httpx.AsyncClient(timeout=10.0) as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
    access_token = token_resp.json().get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="GitHub token exchange failed")

    gh_headers = {"Authorization": f"token {access_token}", "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        user_data = (await client.get("https://api.github.com/user", headers=gh_headers)).json()

    email = user_data.get("email")
    if not email:
        async with httpx.AsyncClient(timeout=10.0) as client:
            emails = (await client.get("https://api.github.com/user/emails", headers=gh_headers)).json()
        primary = next(
            (e for e in emails if isinstance(e, dict) and e.get("primary") and e.get("verified")),
            None,
        )
        if primary:
            email = primary["email"]

    user = await db.fetchrow(
        """
        INSERT INTO users (github_id, github_login, name, email, avatar_url)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (github_id) DO UPDATE SET
            github_login   = EXCLUDED.github_login,
            name           = EXCLUDED.name,
            avatar_url     = EXCLUDED.avatar_url,
            last_active_at = NOW()
        RETURNING id, github_login
        """,
        str(user_data["id"]),
        user_data["login"],
        user_data.get("name") or user_data["login"],
        email,
        user_data.get("avatar_url"),
    )

    token = _make_jwt(str(user["id"]), user["github_login"])
    return RedirectResponse(
        url=f"http://localhost:5173/auth/callback?token={token}",
        status_code=302,
    )


@router.post("/auth/dev-login")
async def dev_login():
    """
    DEV-ONLY login bypass: returns a real JWT for a local test user without
    the GitHub OAuth round-trip. Only available when DEV_MODE=true; returns
    404 otherwise so the route is invisible in production.
    """
    if not settings.DEV_MODE:
        raise HTTPException(status_code=404, detail="Not Found")

    user = await db.fetchrow(
        """
        INSERT INTO users (github_id, github_login, name, email, avatar_url)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (github_id) DO UPDATE SET last_active_at = NOW()
        RETURNING id, github_login
        """,
        "dev-000",
        "dev_tester",
        "Dev Tester",
        "dev@proofforge.local",
        "https://avatars.githubusercontent.com/u/583231",
    )
    token = _make_jwt(str(user["id"]), user["github_login"])
    logger.warning("DEV_MODE login issued for dev_tester — disable DEV_MODE in production")
    return {"access_token": token, "token_type": "bearer", "github_login": user["github_login"]}


@router.post("/auth/refresh")
async def refresh_token(current_user: dict = Depends(get_current_user)):
    token = _make_jwt(str(current_user["id"]), current_user["github_login"])
    return {"access_token": token, "token_type": "bearer"}


@router.post("/auth/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    current_user: dict = Depends(get_current_user),
):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        jti = payload.get("jti") or hashlib.sha256(token.encode()).hexdigest()[:32]
        exp = payload.get("exp")
        ttl = max(1, int(exp - datetime.now(timezone.utc).timestamp())) if exp else 3600
        await redis_module.get_redis().setex(f"blacklist:{jti}", ttl, "1")
    except JWTError:
        pass
    return {"message": "logged out"}


def _make_jwt(user_id: str, github_login: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "github_login": github_login,
        "jti": secrets.token_hex(16),
        "iat": now,
        "exp": now + timedelta(hours=settings.JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
