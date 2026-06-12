# BROKEN: response keys do not match the documented contract; unknown users 500.
from fastapi import FastAPI

app = FastAPI()

USERS = {
    1: {"username": "alice", "email": "alice@example.com", "joined": "2025-03-14"},
    2: {"username": "bob", "email": "bob@example.com", "joined": "2025-07-02"},
}


@app.get("/api/profile/{user_id}")
async def get_profile(user_id: int):
    user = USERS.get(user_id)
    return {
        "Id": str(user_id),
        "user_name": user["username"],
        "EmailAddress": user["email"],
        "joined_date": user["joined"],
    }
