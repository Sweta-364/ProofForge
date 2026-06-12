"""Hidden edge cases."""
import re
from pathlib import Path

STARTER = Path(__file__).resolve().parent.parent.parent / "starter"


def conf():
    return (STARTER / "nginx.conf").read_text(encoding="utf-8")


def test_forwarded_proto_present():
    assert re.search(r"proxy_set_header\s+X-Forwarded-Proto", conf())


def test_upload_size_limited():
    assert re.search(r"client_max_body_size\s+\d+", conf()), (
        "limit request body size with client_max_body_size"
    )
