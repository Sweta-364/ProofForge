from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

ACCOUNTS = {"alice": "Wonderland!42"}


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/login")
async def login(payload: LoginRequest):
    if ACCOUNTS.get(payload.username) != payload.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"access_token": f"token-{payload.username}", "token_type": "bearer"}
