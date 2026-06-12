import sys
from html.parser import HTMLParser
from pathlib import Path


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []          # list of (tag, attrs_dict)
        self.labels = []        # list of dicts: {"for": ..., "text": ...}
        self._open_label = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if tag == "label":
            self._open_label = {"for": attrs.get("for"), "text": ""}

    def handle_data(self, data):
        if self._open_label is not None:
            self._open_label["text"] += data

    def handle_endtag(self, tag):
        if tag == "label" and self._open_label is not None:
            self.labels.append(self._open_label)
            self._open_label = None


def parse_page(starter_dir):
    src = (Path(starter_dir) / "index.html").read_text(encoding="utf-8")
    parser = PageParser()
    parser.feed(src)
    return parser
