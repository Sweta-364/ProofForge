"""Hidden edge cases."""
from pathlib import Path

from tests.ci_helper import workflow_config

STARTER = Path(__file__).resolve().parent.parent.parent / "starter"


def test_checkout_runs_before_setup():
    steps = workflow_config(STARTER)["jobs"]["test"]["steps"]
    uses = [s.get("uses", "") for s in steps]
    checkout_idx = next(
        (i for i, u in enumerate(uses) if u.startswith("actions/checkout")), None
    )
    setup_idx = next(
        (i for i, u in enumerate(uses) if u.startswith("actions/setup-python")), None
    )
    assert checkout_idx is not None
    assert setup_idx is None or checkout_idx < setup_idx


def test_push_trigger_limited_to_main():
    config = workflow_config(STARTER)
    raw = config.get("on", config.get(True))
    if isinstance(raw, dict) and isinstance(raw.get("push"), dict):
        branches = raw["push"].get("branches", [])
        assert "main" in branches
