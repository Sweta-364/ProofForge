import importlib

import starter.settings as settings_module


def reload_with_env(monkeypatch, **env):
    for key in ("DATABASE_URL", "API_KEY", "DEBUG"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return importlib.reload(settings_module)
