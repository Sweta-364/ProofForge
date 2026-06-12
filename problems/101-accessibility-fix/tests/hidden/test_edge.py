"""Hidden edge cases."""
from pathlib import Path

from tests.page_helper import parse_page

STARTER = Path(__file__).resolve().parent.parent.parent / "starter"


def test_labels_have_visible_text():
    page = parse_page(STARTER)
    for lbl in page.labels:
        assert lbl["text"].strip(), "labels must contain visible text"


def test_inputs_keep_name_attributes():
    page = parse_page(STARTER)
    names = {attrs.get("name") for tag, attrs in page.tags if tag == "input"}
    assert {"email", "password"} <= names, "do not remove the input name attributes"
