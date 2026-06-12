#!/usr/bin/env python3
"""
Seed script: tar.gz each problem's starter + tests, upload to MinIO,
and upsert a row in the problems table.

Usage (from repo root, with all services running):
    python backend/migrations/002_seed_problems.py
"""
import asyncio
import json
import logging
import sys
import tarfile
import tempfile
from pathlib import Path

# Allow importing app.* from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import db, minio as minio_module
from app.config import settings  # noqa: F401 — triggers .env load

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
)
logger = logging.getLogger(__name__)

PROBLEMS_DIR = Path(__file__).parent.parent.parent / "problems"


def _make_tarball(source_dir: Path, output_path: Path, arc_prefix: str = "") -> None:
    """Create a .tar.gz archive of all files under source_dir (stripped to root,
    optionally re-rooted under arc_prefix)."""
    with tarfile.open(output_path, "w:gz") as tar:
        for item in sorted(source_dir.rglob("*")):
            if item.is_file():
                arcname = Path(arc_prefix) / item.relative_to(source_dir)
                tar.add(item, arcname=str(arcname))


async def seed_problem(slug_dir: Path) -> None:
    meta_path = slug_dir / "meta.json"
    if not meta_path.exists():
        logger.warning("Skipping %s — no meta.json", slug_dir.name)
        return

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    slug = meta["slug"]
    logger.info("Seeding: %s", slug)

    with tempfile.TemporaryDirectory() as tmpdir:
        starter_archive = Path(tmpdir) / f"{slug}-starter.tar.gz"
        tests_archive = Path(tmpdir) / f"{slug}-tests.tar.gz"

        # The whole pipeline addresses starter files as "starter/<file>"
        # (tests import `from starter.main import app`), so keep the prefix.
        # Test archives are extracted into workspace/tests/ — strip to root.
        _make_tarball(slug_dir / "starter", starter_archive, arc_prefix="starter")
        _make_tarball(slug_dir / "tests", tests_archive)

        starter_key = f"starters/{slug}.tar.gz"
        tests_key = f"tests/{slug}.tar.gz"

        minio_module.upload_file(minio_module.PROBLEMS_BUCKET, starter_key, str(starter_archive))
        minio_module.upload_file(minio_module.PROBLEMS_BUCKET, tests_key, str(tests_archive))
        logger.info("  Uploaded %s and %s", starter_key, tests_key)

    await db.execute(
        """
        INSERT INTO problems (
            slug, title, description, difficulty, category, track, language,
            docker_image, codebase_key, test_suite_key, time_limit_mins, points,
            display_order, is_active, optimal_hint
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, TRUE, $14)
        ON CONFLICT (slug) DO UPDATE SET
            title          = EXCLUDED.title,
            description    = EXCLUDED.description,
            difficulty     = EXCLUDED.difficulty,
            category       = EXCLUDED.category,
            track          = EXCLUDED.track,
            codebase_key   = EXCLUDED.codebase_key,
            test_suite_key = EXCLUDED.test_suite_key,
            display_order  = EXCLUDED.display_order,
            optimal_hint   = EXCLUDED.optimal_hint
        """,
        slug,
        meta["title"],
        meta.get("description", ""),
        meta["difficulty"],
        meta["category"],
        meta["track"],
        meta["language"],
        meta["docker_image"],
        f"starters/{slug}.tar.gz",
        f"tests/{slug}.tar.gz",
        meta["time_limit_mins"],
        meta["points"],
        meta["display_order"],
        meta.get("optimal_hint"),
    )
    logger.info("  DB row upserted for %s", slug)


async def main() -> None:
    await db.init_pool()
    minio_module.init_minio()
    minio_module.ensure_buckets()

    try:
        problem_dirs = sorted(
            d for d in PROBLEMS_DIR.iterdir()
            if d.is_dir() and (d / "meta.json").exists()
        )
        if not problem_dirs:
            logger.error("No problem directories found in %s", PROBLEMS_DIR)
            sys.exit(1)

        for slug_dir in problem_dirs:
            await seed_problem(slug_dir)

        logger.info("=== Seeding complete — %d problems ===", len(problem_dirs))
    finally:
        await db.close_pool()


if __name__ == "__main__":
    asyncio.run(main())
