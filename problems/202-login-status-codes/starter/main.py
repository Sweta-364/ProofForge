# BROKEN: wrong credentials return 200; missing fields crash with KeyError.
from fastapi import FastAPI

app = FastAPI()

ACCOUNTS = {"alice": "Wonderland!42"}


@app.post("/api/login")
async def login(payload: dict):
    username = payload["username"]
    password = payload["password"]
    if ACCOUNTS.get(username) != password:
        return {"error": "invalid credentials"}
    return {"access_token": f"token-{username}", "token_type": "bearer"}
