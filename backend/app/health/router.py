import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app import db, redis as redis_module, minio as minio_module

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Deep health check: verifies DB, Redis, and MinIO connectivity."""
    results: dict[str, str] = {}
    http_status = 200

    # --- PostgreSQL ---
    try:
        await db.fetchval("SELECT 1")
        results["db"] = "ok"
    except Exception as exc:
        logger.error("DB health check failed: %s", exc)
        results["db"] = "error"
        http_status = 503

    # --- Redis ---
    try:
        r = redis_module.get_redis()
        await r.ping()
        results["redis"] = "ok"
    except Exception as exc:
        logger.error("Redis health check failed: %s", exc)
        results["redis"] = "error"
        http_status = 503

    # --- MinIO ---
    try:
        client = minio_module.get_client()
        client.list_buckets()
        results["minio"] = "ok"
    except Exception as exc:
        logger.error("MinIO health check failed: %s", exc)
        results["minio"] = "error"
        http_status = 503

    overall = "ok" if http_status == 200 else "degraded"
    return JSONResponse(
        status_code=http_status,
        content={"status": overall, "version": "0.1.0", **results},
    )


@router.get("/health/ready")
async def readiness():
    """Shallow readiness probe for load balancers."""
    return {"ready": True}
