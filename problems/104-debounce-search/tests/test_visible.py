"""Visible tests - static checks for a correct debounce."""
import re
from pathlib import Path

STARTER = Path(__file__).resolve().parent.parent / "starter"


def src():
    return (STARTER / "debounce.js").read_text(encoding="utf-8")


def test_previous_timer_is_cleared():
    assert "clearTimeout(" in src(), "cancel the previous timer with clearTimeout"


def test_timer_handle_is_stored():
    assert re.search(r"=\s*setTimeout\s*\(", src()), (
        "store the handle returned by setTimeout so it can be cleared"
    )


def test_clear_happens_before_reschedule():
    code = src()
    clear_pos = code.find("clearTimeout(")
    set_pos = code.find("setTimeout(")
    assert clear_pos != -1 and clear_pos < set_pos, (
        "clear the old timer before scheduling the new one"
    )
