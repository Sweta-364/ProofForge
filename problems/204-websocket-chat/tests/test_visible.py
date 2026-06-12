"""Visible tests - the documented websocket protocol."""
import pytest
from fastapi.testclient import TestClient
from starter.main import MESSAGES, app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_history():
    MESSAGES.clear()
    yield
    MESSAGES.clear()


def test_reply_is_json_with_timestamp():
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"user": "alice", "text": "hi"})
        message = ws.receive_json()
    assert message["user"] == "alice"
    assert message["text"] == "hi"
    assert isinstance(message.get("timestamp"), (int, float))


def test_messages_are_recorded_in_history():
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"user": "alice", "text": "hello history"})
        ws.receive_json()
    history = client.get("/api/messages").json()["messages"]
    assert len(history) == 1
    assert history[0]["text"] == "hello history"
