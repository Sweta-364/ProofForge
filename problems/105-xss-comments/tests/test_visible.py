"""Visible tests - static checks that user data never reaches raw-HTML APIs."""
import re
from pathlib import Path

STARTER = Path(__file__).resolve().parent.parent / "starter"

# innerHTML assignment that interpolates a template literal or concatenates a variable
UNSAFE_INNERHTML = re.compile(
    r"innerHTML\s*\+?=\s*(`[^`]*\$\{|[^;]*\+\s*\w)"
)


def src():
    return (STARTER / "comments.js").read_text(encoding="utf-8")


def test_no_user_data_in_innerhtml():
    assert not UNSAFE_INNERHTML.search(src()), (
        "user-controlled values are interpolated into innerHTML (XSS)"
    )


def test_uses_safe_dom_api_or_escaping():
    code = src()
    safe = ("textContent" in code) or ("createTextNode" in code) or ("escapeHtml" in code)
    assert safe, "render the comment via textContent/createTextNode or escape it"
