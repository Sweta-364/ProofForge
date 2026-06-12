"""Visible tests - the audit findings, automated."""
from pathlib import Path

from tests.page_helper import parse_page

STARTER = Path(__file__).resolve().parent.parent / "starter"


def test_html_has_lang():
    page = parse_page(STARTER)
    html_attrs = next(attrs for tag, attrs in page.tags if tag == "html")
    assert html_attrs.get("lang"), "<html> needs a lang attribute"


def test_all_images_have_alt_text():
    page = parse_page(STARTER)
    for tag, attrs in page.tags:
        if tag == "img":
            assert attrs.get("alt"), f"img {attrs.get('src')} has no alt text"


def test_inputs_have_labels():
    page = parse_page(STARTER)
    label_targets = {lbl["for"] for lbl in page.labels if lbl["for"]}
    for tag, attrs in page.tags:
        if tag == "input" and attrs.get("type") in ("text", "email", "password"):
            ok = (attrs.get("id") in label_targets) or attrs.get("aria-label")
            assert ok, f"input name={attrs.get('name')} has no associated label"


def test_button_declares_type():
    page = parse_page(STARTER)
    buttons = [attrs for tag, attrs in page.tags if tag == "button"]
    assert buttons, "expected a form button"
    for attrs in buttons:
        assert attrs.get("type") == "submit", "form button should declare type=submit"
