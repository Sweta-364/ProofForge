"""Hidden edge cases."""
import pytest
from fastapi.testclient import TestClient
from starter.main import MESSAGES, app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_history():
    MESSAGES.clear()
    yield
    MESSAGES.clear()


def test_multiple_messages_keep_order():
    with client.websocket_connect("/ws/chat") as ws:
        for i in range(3):
            ws.send_json({"user": "alice", "text": f"msg-{i}"})
            ws.receive_json()
    history = client.get("/api/messages").json()["messages"]
    assert [m["text"] for m in history] == ["msg-0", "msg-1", "msg-2"]


def test_history_survives_reconnect():
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"user": "alice", "text": "first session"})
        ws.receive_json()
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"user": "bob", "text": "second session"})
        ws.receive_json()
    history = client.get("/api/messages").json()["messages"]
    assert len(history) == 2
