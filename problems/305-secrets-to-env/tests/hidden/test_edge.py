"""Hidden edge cases."""
from tests.settings_helper import reload_with_env


def test_api_key_read_from_env(monkeypatch):
    mod = reload_with_env(monkeypatch, API_KEY="from-the-environment")
    assert mod.get_api_key() == "from-the-environment"


def test_debug_parses_truthy_strings(monkeypatch):
    mod = reload_with_env(monkeypatch, DEBUG="true")
    assert mod.is_debug() is True


def test_default_database_url_has_no_credentials(monkeypatch):
    mod = reload_with_env(monkeypatch)
    url = mod.get_database_url()
    assert "@" not in url.split("//", 1)[-1].split("/")[0] or ":" not in url.split("@")[0].split("//")[-1], (
        "the fallback DATABASE_URL must not embed a password"
    )
