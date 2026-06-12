"""Hidden edge cases."""
import re
from pathlib import Path

STARTER = Path(__file__).resolve().parent.parent.parent / "starter"


def src():
    return (STARTER / "debounce.js").read_text(encoding="utf-8")


def test_debounce_still_returns_a_function():
    assert re.search(r"return\s+(function|\()", src()), (
        "debounce must still return a wrapper function"
    )


def test_cleartimeout_uses_stored_handle():
    assert re.search(r"clearTimeout\s*\(\s*\w+", src()), (
        "clearTimeout must be called with the stored timer handle"
    )


def test_arguments_still_forwarded():
    assert re.search(r"fn\s*(\.apply|\.call|\()", src()), (
        "the wrapped function must still be invoked with its arguments"
    )
