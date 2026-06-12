"""Visible tests - the responsive requirements, automated."""
import re
from pathlib import Path

from tests.css_helper import media_blocks, read_css, read_html

STARTER = Path(__file__).resolve().parent.parent / "starter"


def test_viewport_meta_present():
    html = read_html(STARTER)
    assert re.search(r'<meta[^>]+name=["\']viewport["\']', html), (
        "index.html needs a viewport meta tag"
    )


def test_container_is_not_fixed_width():
    css = read_css(STARTER)
    assert not re.search(r"(?<![-\w])width\s*:\s*900px", css), (
        "replace the hardcoded width: 900px with max-width"
    )
    assert re.search(r"max-width\s*:\s*900px", css), "keep the 900px desktop cap via max-width"


def test_mobile_breakpoint_stacks_layout():
    css = read_css(STARTER)
    assert re.search(r"@media[^{]*max-width\s*:\s*768px", css), "add a 768px breakpoint"
    matching = [
        b for b in media_blocks(css)
        if ".layout" in b and re.search(r"flex-direction\s*:\s*column", b)
    ]
    assert matching, "the media query must stack .layout with flex-direction: column"
