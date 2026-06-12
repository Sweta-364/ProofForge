"""Hidden edge cases."""
from pathlib import Path

import yaml

STARTER = Path(__file__).resolve().parent.parent.parent / "starter"


def load_compose():
    return yaml.safe_load((STARTER / "docker-compose.yml").read_text(encoding="utf-8"))


def test_healthcheck_has_interval_and_retries():
    healthcheck = load_compose()["services"]["db"].get("healthcheck") or {}
    assert "interval" in healthcheck and "retries" in healthcheck


def test_services_have_restart_policy():
    services = load_compose()["services"]
    for name in ("db", "web"):
        assert services[name].get("restart") in ("unless-stopped", "always"), (
            f"{name} needs a restart policy"
        )
