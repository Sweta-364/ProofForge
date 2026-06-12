import re
from pathlib import Path


def read_css(starter_dir):
    return (Path(starter_dir) / "styles.css").read_text(encoding="utf-8")


def read_html(starter_dir):
    return (Path(starter_dir) / "index.html").read_text(encoding="utf-8")


def media_blocks(css, needle="max-width"):
    """Return the body text of every @media block (handles nested braces)."""
    blocks = []
    for m in re.finditer(r"@media[^{]*\{", css):
        if needle not in css[m.start():m.end()]:
            continue
        depth = 1
        i = m.end()
        while i < len(css) and depth:
            if css[i] == "{":
                depth += 1
            elif css[i] == "}":
                depth -= 1
            i += 1
        blocks.append(css[m.end():i - 1])
    return blocks
