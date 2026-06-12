import math

from fastapi import FastAPI

app = FastAPI()

ITEMS = [{"id": i, "name": f"Item {i}"} for i in range(1, 26)]


@app.get("/api/items")
async def list_items(page: int = 1, page_size: int = 10):
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": ITEMS[start:end],
        "page": page,
        "page_size": page_size,
        "total": len(ITEMS),
        "total_pages": math.ceil(len(ITEMS) / page_size),
    }
