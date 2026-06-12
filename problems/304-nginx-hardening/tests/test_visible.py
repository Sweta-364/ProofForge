"""Visible tests - the scan findings."""
import re
from pathlib import Path

STARTER = Path(__file__).resolve().parent.parent / "starter"


def conf():
    return (STARTER / "nginx.conf").read_text(encoding="utf-8")


def test_version_disclosure_disabled():
    assert re.search(r"server_tokens\s+off\s*;", conf()), "add server_tokens off;"


def test_gzip_enabled():
    assert re.search(r"(?<!#)\bgzip\s+on\s*;", conf()), "enable gzip compression"


def test_security_headers_present():
    text = conf()
    assert re.search(r"add_header\s+X-Frame-Options\s+(DENY|SAMEORIGIN)", text), (
        "add the X-Frame-Options header"
    )
    assert re.search(r"add_header\s+X-Content-Type-Options\s+nosniff", text), (
        "add the X-Content-Type-Options header"
    )


def test_proxy_forwards_client_info():
    text = conf()
    assert re.search(r"proxy_set_header\s+Host\s+\$host", text), (
        "forward the Host header to the app"
    )
    assert re.search(r"proxy_set_header\s+X-Forwarded-For", text), (
        "forward X-Forwarded-For to the app"
    )
