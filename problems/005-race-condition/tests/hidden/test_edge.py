"""Hidden edge-case tests — validate the race-condition fix."""
import asyncio
import pytest
from starter.notification_manager import NotificationManager


@pytest.fixture
def manager():
    m = NotificationManager()
    yield m
    m.reset()


async def test_no_duplicates_concurrent(manager):
    """20 concurrent coroutines sending the same notification_id must produce exactly 1 delivery.
    Currently FAILS with broken code because of the TOCTOU race condition."""
    received = []

    async def capture(msg):
        received.append(msg)

    manager.register("user1", capture)

    # All 20 tasks run concurrently — the await asyncio.sleep(0) in send_notification
    # means all can pass the 'if notification_id in sent_ids' check before any adds to the set
    tasks = [
        manager.send_notification("user1", "race_notif_001", {"text": "event"})
        for _ in range(20)
    ]
    await asyncio.gather(*tasks)

    assert len(received) == 1, (
        f"Expected exactly 1 delivery, got {len(received)}. "
        "Fix: wrap the check-then-add in asyncio.Lock() to make it atomic."
    )


async def test_different_ids_all_delivered(manager):
    """10 different notification_ids must all be delivered exactly once."""
    received = []

    async def capture(msg):
        received.append(msg)

    manager.register("user1", capture)

    tasks = [
        manager.send_notification("user1", f"notif_{i:03d}", {"seq": i})
        for i in range(10)
    ]
    await asyncio.gather(*tasks)

    assert len(received) == 10, (
        f"Expected 10 deliveries for 10 unique IDs, got {len(received)}. "
        "Different notification_ids must each be delivered once."
    )


async def test_lock_prevents_toctou_rapid_fire(manager):
    """100 concurrent sends of the same notification_id must yield exactly 1 delivery."""
    received = []

    async def capture(msg):
        received.append(msg)

    manager.register("user1", capture)

    tasks = [
        manager.send_notification("user1", "rapid_fire_001", {"burst": True})
        for _ in range(100)
    ]
    await asyncio.gather(*tasks)

    assert len(received) == 1, (
        f"Rapid-fire 100 concurrent sends produced {len(received)} deliveries. "
        "asyncio.Lock() must protect the check-and-add operation atomically."
    )


async def test_multiple_users_no_cross_contamination(manager):
    """Notifications to different users must be independent."""
    received_a: list = []
    received_b: list = []

    manager.register("user_a", lambda m: received_a.append(m))
    manager.register("user_b", lambda m: received_b.append(m))

    await asyncio.gather(
        manager.send_notification("user_a", "notif_for_a", {"user": "a"}),
        manager.send_notification("user_b", "notif_for_b", {"user": "b"}),
    )

    assert len(received_a) == 1
    assert len(received_b) == 1
    assert received_a[0]["user"] == "a"
    assert received_b[0]["user"] == "b"
