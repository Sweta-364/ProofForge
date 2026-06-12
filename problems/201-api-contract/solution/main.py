from fastapi import FastAPI, HTTPException

app = FastAPI()

USERS = {
    1: {"username": "alice", "email": "alice@example.com", "joined": "2025-03-14"},
    2: {"username": "bob", "email": "bob@example.com", "joined": "2025-07-02"},
}


@app.get("/api/profile/{user_id}")
async def get_profile(user_id: int):
    user = USERS.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user_id,
        "username": user["username"],
        "email": user["email"],
        "joined": user["joined"],
    }
