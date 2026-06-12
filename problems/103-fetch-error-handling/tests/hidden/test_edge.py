"""Hidden edge cases."""
import re
from pathlib import Path

STARTER = Path(__file__).resolve().parent.parent.parent / "starter"


def src():
    return (STARTER / "app.js").read_text(encoding="utf-8")


def test_ok_checked_before_parsing_body():
    code = src()
    ok_pos = code.find(".ok")
    if ok_pos == -1:
        ok_pos = code.find(".status")
    json_pos = code.find(".json(")
    assert ok_pos != -1 and ok_pos < json_pos, (
        "validate the response before calling response.json()"
    )


def test_error_messages_are_not_empty():
    for call in re.findall(r"showError\s*\(([^)]*)\)", src()):
        stripped = call.strip()
        if stripped.startswith(("'", '"', "`")):
            assert len(stripped) > 4, "error messages should be human readable"
