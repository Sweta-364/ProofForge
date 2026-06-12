# BROKEN: no extension or size validation at all.
from fastapi import FastAPI, Request

app = FastAPI()

MAX_BYTES = 1024 * 1024
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf"}


@app.post("/api/upload")
async def upload(request: Request, filename: str):
    body = await request.body()
    return {"filename": filename, "size": len(body), "status": "stored"}
