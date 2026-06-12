import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost:5432/shop")
API_KEY = os.environ.get("API_KEY", "")
DEBUG = os.environ.get("DEBUG", "false").lower() in ("1", "true", "yes")


def get_database_url() -> str:
    return DATABASE_URL


def get_api_key() -> str:
    return API_KEY


def is_debug() -> bool:
    return DEBUG
