from fastapi import FastAPI, HTTPException, Request

app = FastAPI()

MAX_BYTES = 1024 * 1024
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf"}


@app.post("/api/upload")
async def upload(request: Request, filename: str):
    if "." not in filename:
        raise HTTPException(status_code=415, detail="Unsupported file type")
    extension = filename.rsplit(".", 1)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Unsupported file type")

    body = await request.body()
    if len(body) == 0:
        raise HTTPException(status_code=400, detail="Empty upload")
    if len(body) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large")

    return {"filename": filename, "size": len(body), "status": "stored"}
