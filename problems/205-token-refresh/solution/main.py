import secrets
import time

from fastapi import FastAPI, HTTPException

app = FastAPI()

ACCOUNTS = {"alice": "Wonderland!42"}
REFRESH_TTL = 3600
REFRESH_TOKENS: dict[str, dict] = {}


@app.post("/api/auth/login")
async def login(payload: dict):
    username = payload.get("username")
    password = payload.get("password")
    if ACCOUNTS.get(username) != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    refresh_token = secrets.token_hex(16)
    REFRESH_TOKENS[refresh_token] = {"username": username, "created_at": time.time()}
    return {"access_token": secrets.token_hex(8), "refresh_token": refresh_token}


@app.post("/api/auth/refresh")
async def refresh(payload: dict):
    token = payload.get("refresh_token", "")
    entry = REFRESH_TOKENS.get(token)
    if entry is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if time.time() - entry["created_at"] > REFRESH_TTL:
        del REFRESH_TOKENS[token]
        raise HTTPException(status_code=401, detail="Refresh token expired")

    del REFRESH_TOKENS[token]
    new_refresh = secrets.token_hex(16)
    REFRESH_TOKENS[new_refresh] = {
        "username": entry["username"],
        "created_at": time.time(),
    }
    return {"access_token": secrets.token_hex(8), "refresh_token": new_refresh}
