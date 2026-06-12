# notification_manager.py — WebSocket notification handler with race condition
import asyncio
import logging
from typing import Callable

logger = logging.getLogger(__name__)


class NotificationManager:
    def __init__(self):
        self.connections: dict[str, Callable] = {}
        # BUG: This set is accessed from multiple coroutines without a lock.
        # The check-then-add is a TOCTOU race condition.
        self.sent_ids: set = set()

    def register(self, user_id: str, send_func: Callable) -> None:
        self.connections[user_id] = send_func

    def unregister(self, user_id: str) -> None:
        self.connections.pop(user_id, None)

    async def send_notification(
        self, user_id: str, notification_id: str, message: dict
    ) -> None:
        """Send a notification to a user, deduplicating by notification_id."""
        # BUG: TOCTOU — both coroutines can pass this check before either adds to the set
        if notification_id in self.sent_ids:
            return

        # await yields control — another coroutine can now pass the check above
        await asyncio.sleep(0)

        # Another coroutine may have already added this before we get here
        self.sent_ids.add(notification_id)

        if user_id in self.connections:
            await self.connections[user_id](message)
            logger.info("Sent notification %s to %s", notification_id, user_id)

    def get_sent_count(self) -> int:
        return len(self.sent_ids)

    def reset(self) -> None:
        """Reset state (test helper)."""
        self.sent_ids.clear()
        self.connections.clear()
