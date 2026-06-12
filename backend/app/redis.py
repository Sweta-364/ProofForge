import json
import logging
from typing import AsyncIterator

import aioredis

from app.config import settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


async def init_redis() -> None:
    global _redis
    _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    await _redis.ping()
    logger.info("aioredis pool ready")


async def close_redis() -> None:
    if _redis:
        await _redis.close()
        logger.info("aioredis pool closed")


def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialised — call init_redis() first")
    return _redis


async def publish(channel: str, message_dict: dict) -> None:
    await _redis.publish(channel, json.dumps(message_dict))


async def subscribe(channel: str) -> AsyncIterator[dict]:
    """Async generator that yields decoded message dicts from a pub/sub channel."""
    pubsub = _redis.pubsub()
    await pubsub.subscribe(channel)
    try:
        async for message in pubsub.listen():
            if message and message.get("type") == "message":
                yield json.loads(message["data"])
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
