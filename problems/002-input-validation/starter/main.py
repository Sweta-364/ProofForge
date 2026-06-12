# BROKEN: Password encoding uses ascii instead of utf-8.
# Bug: password.encode('ascii') raises UnicodeEncodeError for non-ASCII characters
# (accented letters like é, ü, or emoji like 🔑).
# There is also no error handling, so any exception becomes a 500.
import bcrypt
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# Stored hashes — computed correctly with utf-8 at startup
# alice's password: "password" (ASCII only — works with both ascii and utf-8)
# bob's password:   "secur3#pass" (ASCII only — used for correct-login test)
# carol's password: "café" (contains é — non-ASCII, triggers the bug)
_USERS: dict[str, bytes] = {
    "alice": bcrypt.hashpw("password".encode("utf-8"), bcrypt.gensalt()),
    "bob":   bcrypt.hashpw("secur3#pass".encode("utf-8"), bcrypt.gensalt()),
    "carol": bcrypt.hashpw("café".encode("utf-8"), bcrypt.gensalt()),
}


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    stored_hash = _USERS.get(request.username)
    if stored_hash is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # BUG: encode('ascii') raises UnicodeEncodeError for passwords with non-ASCII chars
    # No try/except means the exception propagates as HTTP 500
    password_bytes = request.password.encode("ascii")
    if bcrypt.checkpw(password_bytes, stored_hash):
        return {"access_token": "mock-token", "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid credentials")
