"""
Health endpoint tests.

All tests use the sync TestClient (from conftest) so no async/await is needed
in the test functions themselves.

Service-failure tests patch module-level globals inside app.db / app.redis /
app.minio.  unittest.mock.patch replaces the attribute in the module's __dict__,
which is shared across threads, so patches are visible to the request handler
running inside TestClient's internal thread.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Happy-path ────────────────────────────────────────────────────────────────

def test_health_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"
    assert data["redis"] == "ok"
    assert data["minio"] == "ok"
    assert data["version"] == "0.1.0"


def test_health_ready(client):
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"ready": True}


# ── Service-failure paths (503) ───────────────────────────────────────────────

def test_health_db_failure_returns_503(client):
    """When the DB is unreachable the health endpoint must return 503."""
    with patch("app.db.fetchval", new_callable=AsyncMock, side_effect=Exception("connection refused")):
        response = client.get("/api/v1/health")
    assert response.status_code == 503
    data = response.json()
    assert data["db"] == "error"
    assert data["status"] == "degraded"


def test_health_redis_failure_returns_503(client):
    """When Redis is unreachable the health endpoint must return 503."""
    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock(side_effect=Exception("connection refused"))
    with patch("app.redis._redis", mock_redis):
        response = client.get("/api/v1/health")
    assert response.status_code == 503
    data = response.json()
    assert data["redis"] == "error"
    assert data["status"] == "degraded"


def test_health_minio_failure_returns_503(client):
    """When MinIO is unreachable the health endpoint must return 503."""
    mock_minio = MagicMock()
    mock_minio.list_buckets.side_effect = Exception("connection refused")
    with patch("app.minio._client", mock_minio):
        response = client.get("/api/v1/health")
    assert response.status_code == 503
    data = response.json()
    assert data["minio"] == "error"
    assert data["status"] == "degraded"


def test_health_partial_failure_still_503(client):
    """Even a single failed service must make the overall status degraded."""
    with patch("app.db.fetchval", new_callable=AsyncMock, side_effect=Exception("timeout")):
        response = client.get("/api/v1/health")
    assert response.status_code == 503
    data = response.json()
    # Only DB failed — Redis and MinIO should still report ok
    assert data["db"] == "error"
    assert data["redis"] == "ok"
    assert data["minio"] == "ok"
