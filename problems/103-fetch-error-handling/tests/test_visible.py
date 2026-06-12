"""Visible tests - static checks for the required error handling."""
import re
from pathlib import Path

STARTER = Path(__file__).resolve().parent.parent / "starter"


def src():
    return (STARTER / "app.js").read_text(encoding="utf-8")


def test_checks_response_ok():
    assert re.search(r"\.ok\b|\.status\b", src()), (
        "check response.ok (or response.status) before using the body"
    )


def test_handles_network_errors():
    code = src()
    has_try_catch = re.search(r"\btry\b", code) and re.search(r"\bcatch\b", code)
    has_promise_catch = ".catch(" in code
    assert has_try_catch or has_promise_catch, "network failures must be caught"


def test_shows_error_to_user():
    calls = len(re.findall(r"showError\s*\(", src()))
    assert calls >= 2, "call showError() when the request fails (it is currently never called)"
