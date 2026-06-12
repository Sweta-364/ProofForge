# BROKEN: refresh accepts any string, never expires tokens, never rotates them.
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
    return {"access_token": secrets.token_hex(8), "refresh_token": token}
