"""Visible tests — demonstrate the expected notification behaviour."""
import asyncio
import pytest
from starter.notification_manager import NotificationManager


@pytest.fixture
def manager():
    m = NotificationManager()
    yield m
    m.reset()


async def test_single_notification_delivered(manager):
    """One connection receiving one notification — delivered exactly once."""
    received = []

    async def capture(msg):
        received.append(msg)

    manager.register("user1", capture)
    await manager.send_notification("user1", "notif_001", {"text": "hello"})

    assert len(received) == 1
    assert received[0] == {"text": "hello"}


async def test_dedup_same_id_sequential(manager):
    """Sending the same notification_id twice sequentially delivers it once."""
    received = []

    async def capture(msg):
        received.append(msg)

    manager.register("user1", capture)
    await manager.send_notification("user1", "notif_dup", {"text": "first"})
    await manager.send_notification("user1", "notif_dup", {"text": "second"})

    assert len(received) == 1, (
        f"Expected 1 delivery, got {len(received)}. "
        "The second send with the same notification_id must be a no-op."
    )
