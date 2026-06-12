"""Visible tests - the three reported CI problems."""
from pathlib import Path

from tests.ci_helper import triggers, workflow_config, workflow_text

STARTER = Path(__file__).resolve().parent.parent / "starter"


def test_workflow_triggers_on_push_and_pull_request():
    events = triggers(workflow_config(STARTER))
    assert "pull_request" in events, "pull_request (underscore) is the valid event name"
    assert "push" in events, "pushes to main must also run CI"


def test_workflow_checks_out_the_code():
    config = workflow_config(STARTER)
    steps = config["jobs"]["test"]["steps"]
    uses = [s.get("uses", "") for s in steps]
    assert any(u.startswith("actions/checkout") for u in uses), (
        "add an actions/checkout step"
    )


def test_no_hardcoded_token():
    text = workflow_text(STARTER)
    assert "sk-live" not in text, "remove the hardcoded live token"
    assert "${{ secrets." in text, "read the token from the secrets context"
