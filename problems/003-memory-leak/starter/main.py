"""FastAPI app that uses the leaky auth middleware."""
from fastapi import FastAPI, HTTPException, Header
from starter.auth import verify_token

app = FastAPI()


@app.get("/api/me")
async def get_me(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.removeprefix("Bearer ")
    payload = await verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"user_id": payload.get("sub"), "data": "ok"}
