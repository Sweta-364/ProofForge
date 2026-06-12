"""
WebSocket endpoint for real-time submission status streaming.

Auth: JWT passed as ?token=JWT query param.
Messages are forwarded from Redis pub/sub channel "submission:{id}".
"""
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import jwt, JWTError

from app import db
from app.config import settings
from app.redis import get_redis

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])

# WebSocket close codes
WS_CLOSE_POLICY_VIOLATION = 4001    # auth failure
WS_CLOSE_FORBIDDEN = 4003           # ownership check failed


@router.websocket("/ws/submissions/{submission_id}")
async def ws_submission_status(websocket: WebSocket, submission_id: str):
    token = websocket.query_params.get("token")

    # --- Auth ---
    if not token:
        await websocket.close(code=WS_CLOSE_POLICY_VIOLATION)
        return

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise JWTError("no sub")
    except JWTError:
        await websocket.close(code=WS_CLOSE_POLICY_VIOLATION)
        return

    await websocket.accept()

    # --- Ownership check ---
    submission = await db.fetchrow(
        "SELECT * FROM submissions WHERE id=$1", submission_id
    )
    if not submission or str(submission["user_id"]) != user_id:
        await websocket.close(code=WS_CLOSE_FORBIDDEN)
        return

    # --- Already completed: send final message and close ---
    if submission["status"] == "completed" and submission["review_id"]:
        review = await db.fetchrow(
            "SELECT overall_score, verdict FROM reviews WHERE id=$1",
            submission["review_id"],
        )
        await websocket.send_text(json.dumps({
            "type": "review_complete",
            "submission_id": submission_id,
            "score": review["overall_score"] if review else submission["score"],
            "verdict": review["verdict"] if review else "major_revisions",
            "review_id": str(submission["review_id"]),
        }))
        await websocket.close()
        return

    # --- Subscribe to Redis pub/sub and forward messages ---
    redis = get_redis()
    pubsub = redis.pubsub()
    channel = f"submission:{submission_id}"
    await pubsub.subscribe(channel)

    try:
        async for message in pubsub.listen():
            if not message or message.get("type") != "message":
                continue
            try:
                data = json.loads(message["data"])
            except (json.JSONDecodeError, TypeError):
                continue

            try:
                await websocket.send_text(json.dumps(data))
            except WebSocketDisconnect:
                break
            except Exception:
                break

            # Close cleanly after the terminal event
            if data.get("type") in ("review_complete", "error"):
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning("WebSocket error for submission %s: %s", submission_id, e)
    finally:
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass
