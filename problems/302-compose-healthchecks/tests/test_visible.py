"""Visible tests - compose startup ordering."""
from pathlib import Path

import yaml

STARTER = Path(__file__).resolve().parent.parent / "starter"


def load_compose():
    return yaml.safe_load((STARTER / "docker-compose.yml").read_text(encoding="utf-8"))


def test_db_image_is_pinned():
    image = load_compose()["services"]["db"]["image"]
    assert not image.endswith(":latest") and ":" in image, (
        "pin the postgres image to a specific tag"
    )


def test_db_has_healthcheck():
    db = load_compose()["services"]["db"]
    healthcheck = db.get("healthcheck") or {}
    test_cmd = str(healthcheck.get("test", ""))
    assert "pg_isready" in test_cmd, "db needs a pg_isready healthcheck"


def test_web_waits_for_healthy_db():
    web = load_compose()["services"]["web"]
    depends = web.get("depends_on")
    assert isinstance(depends, dict), "use the long-form depends_on with a condition"
    assert depends.get("db", {}).get("condition") == "service_healthy"
