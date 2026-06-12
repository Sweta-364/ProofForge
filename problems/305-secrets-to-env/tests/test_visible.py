"""Visible tests - configuration must come from the environment."""
from pathlib import Path

import starter.settings as settings_module
from tests.settings_helper import reload_with_env


def test_database_url_read_from_env(monkeypatch):
    mod = reload_with_env(monkeypatch, DATABASE_URL="postgresql://test-host:5432/testdb")
    assert mod.get_database_url() == "postgresql://test-host:5432/testdb"


def test_no_hardcoded_secrets_in_source():
    src = Path(settings_module.__file__).read_text(encoding="utf-8")
    assert "SuperSecret123" not in src, "the production DB password is still in the source"
    assert "sk-live" not in src, "the live API key is still in the source"


def test_debug_defaults_to_false(monkeypatch):
    mod = reload_with_env(monkeypatch)
    assert mod.is_debug() is False, "DEBUG must default to False in production"
