import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

MESSAGES: list[dict] = []


@app.get("/api/messages")
async def get_messages():
    return {"messages": MESSAGES}


@app.websocket("/ws/chat")
async def chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            message = {
                "user": data["user"],
                "text": data["text"],
                "timestamp": time.time(),
            }
            MESSAGES.append(message)
            await websocket.send_json(message)
    except WebSocketDisconnect:
        pass
