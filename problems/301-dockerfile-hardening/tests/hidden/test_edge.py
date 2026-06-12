"""Hidden edge cases."""
from pathlib import Path

from tests.docker_helper import dockerfile_lines

STARTER = Path(__file__).resolve().parent.parent.parent / "starter"


def test_dependencies_installed_before_copying_source():
    lines = dockerfile_lines(STARTER)
    req_copy = next(
        (i for i, l in enumerate(lines)
         if l.upper().startswith("COPY") and "requirements.txt" in l),
        None,
    )
    full_copy = next(
        (i for i, l in enumerate(lines)
         if l.upper().startswith("COPY") and "requirements.txt" not in l),
        None,
    )
    assert req_copy is not None, "COPY requirements.txt separately for layer caching"
    assert full_copy is None or req_copy < full_copy, (
        "install dependencies before copying the full source"
    )


def test_no_latest_tag_anywhere():
    text = (STARTER / "Dockerfile").read_text(encoding="utf-8")
    assert ":latest" not in text
