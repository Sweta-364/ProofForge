"""Shared helper to extract problem tarballs into {path: content} dicts."""
import io
import logging
import tarfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Editable/visible file types across all tracks (backend, frontend, fullstack, devops)
ALLOWED_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".json",
    ".yml", ".yaml", ".conf", ".cfg", ".ini", ".toml", ".txt", ".md",
    ".sh", ".sql", ".env",
}
ALLOWED_FILENAMES = {"Dockerfile", "Makefile", ".dockerignore", ".gitignore"}

MAX_FILES = 50


def is_allowed_file(name: str) -> bool:
    p = Path(name)
    return p.suffix.lower() in ALLOWED_EXTENSIONS or p.name in ALLOWED_FILENAMES


def extract_tar_to_dict(tar_bytes: bytes) -> dict[str, str]:
    """Extract allowed text files from a tar.gz blob -> {relative_path: content}.

    Skips hidden test directories and caches.
    """
    result: dict[str, str] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tar:
            count = 0
            for member in tar.getmembers():
                if count >= MAX_FILES:
                    break
                if not member.isfile():
                    continue
                if not is_allowed_file(member.name):
                    continue
                parts = Path(member.name).parts
                if "hidden" in parts or "__pycache__" in parts:
                    continue
                f = tar.extractfile(member)
                if f is None:
                    continue
                result[member.name] = f.read().decode("utf-8", errors="replace")
                count += 1
    except Exception as e:
        logger.warning("Tar extraction failed: %s", e)
    return result
