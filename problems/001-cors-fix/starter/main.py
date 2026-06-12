# BROKEN: Missing CORS middleware — the frontend cannot call this API.
# Issue: All requests from http://localhost:3000 are blocked by CORS policy.
from fastapi import FastAPI

app = FastAPI()

MOCK_USERS = [
    {"id": 1, "username": "alice", "email": "alice@example.com"},
    {"id": 2, "username": "bob",   "email": "bob@example.com"},
]


@app.get("/api/users")
async def get_users():
    return MOCK_USERS


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/login")
async def login(payload: dict):
    return {"token": "mock-token-abc123"}
