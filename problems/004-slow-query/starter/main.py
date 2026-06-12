"""FastAPI app for the slow-query problem."""
from fastapi import FastAPI
from starter.user_service import search_users, seed_database

app = FastAPI()


@app.on_event("startup")
async def startup():
    seed_database()


@app.get("/api/users/search")
async def search(q: str = ""):
    return search_users(q)
