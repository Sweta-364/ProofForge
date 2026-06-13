import logging
from datetime import timedelta

from minio import Minio
from minio.error import S3Error

from app.config import settings

logger = logging.getLogger(__name__)

PROBLEMS_BUCKET = "problems"
SUBMISSIONS_BUCKET = "submissions"

_client: Minio | None = None


def init_minio() -> None:
    global _client
    _client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=False,
    )
    logger.info("MinIO client created (endpoint=%s)", settings.MINIO_ENDPOINT)


def ensure_buckets() -> None:
    """Create required buckets if they do not exist. Called at startup."""
    for bucket in (PROBLEMS_BUCKET, SUBMISSIONS_BUCKET):
        if not _client.bucket_exists(bucket):
            _client.make_bucket(bucket)
            logger.info("Created MinIO bucket: %s", bucket)
        else:
            logger.info("MinIO bucket exists: %s", bucket)


def get_client() -> Minio:
    if _client is None:
        raise RuntimeError("MinIO not initialised — call init_minio() first")
    return _client


def upload_file(bucket: str, key: str, file_path: str) -> None:
    _client.fput_object(bucket, key, file_path)


def download_file(bucket: str, key: str) -> bytes:
    response = _client.get_object(bucket, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def upload_bytes(bucket: str, key: str, data: bytes, content_type: str = "application/gzip") -> None:
    """Upload raw bytes to MinIO (no temp file on disk)."""
    import io as _io
    _client.put_object(bucket, key, _io.BytesIO(data), length=len(data), content_type=content_type)


def get_presigned_url(bucket: str, key: str, expires: int = 3600) -> str:
    return _client.presigned_get_object(bucket, key, expires=timedelta(seconds=expires))
