import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

from app.config import settings
from app import db, redis as redis_module

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/github", auto_error=True)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        jti: str | None = payload.get("jti")
        if user_id is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    if jti:
        r = redis_module.get_redis()
        if await r.get(f"blacklist:{jti}"):
            raise credentials_exc

    user = await db.fetchrow(
        """
        SELECT id, github_login, name, email, avatar_url, career_track,
               current_difficulty, total_score, issues_resolved, created_at
        FROM users WHERE id = $1
        """,
        user_id,
    )
    if user is None:
        raise credentials_exc
    return dict(user)
