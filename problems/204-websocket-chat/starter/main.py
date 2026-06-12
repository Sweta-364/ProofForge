# BROKEN: replies with plain strings, never records history, crashes on disconnect.
from fastapi import FastAPI, WebSocket

app = FastAPI()

MESSAGES: list[dict] = []


@app.get("/api/messages")
async def get_messages():
    return {"messages": MESSAGES}


@app.websocket("/ws/chat")
async def chat(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_json()
        await websocket.send_text(f"{data['user']}: {data['text']}")
