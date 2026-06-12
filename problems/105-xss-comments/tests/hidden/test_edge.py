"""Hidden edge cases."""
import re
from pathlib import Path

STARTER = Path(__file__).resolve().parent.parent.parent / "starter"


def src():
    return (STARTER / "comments.js").read_text(encoding="utf-8")


def test_no_other_raw_html_sinks_with_user_data():
    code = src()
    for sink in ("insertAdjacentHTML", "outerHTML", "document.write"):
        if sink in code:
            assert not re.search(sink + r"[^;]*(\$\{|\+\s*\w)", code), (
                f"user data must not flow into {sink}"
            )


def test_escape_helper_actually_used_if_present():
    code = src()
    if "function escapeHtml" in code:
        assert len(re.findall(r"escapeHtml\s*\(", code)) >= 2, (
            "escapeHtml is defined but never called"
        )
