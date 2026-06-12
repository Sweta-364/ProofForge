"""Hidden edge cases."""
import re
from pathlib import Path

from tests.css_helper import media_blocks, read_css

STARTER = Path(__file__).resolve().parent.parent.parent / "starter"


def test_sidebar_full_width_on_mobile():
    css = read_css(STARTER)
    blocks = media_blocks(css)
    ok = any(
        ".sidebar" in b and re.search(r"width\s*:\s*(100%|auto)", b)
        for b in blocks
    )
    assert ok, "inside the breakpoint, .sidebar should span the full width"


def test_content_is_flexible():
    css = read_css(STARTER)
    assert not re.search(r"(?<![-\w])width\s*:\s*650px", css), (
        ".content should be flexible, not a hardcoded 650px"
    )
