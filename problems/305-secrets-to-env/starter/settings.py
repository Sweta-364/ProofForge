# BROKEN: production credentials committed to the repository.
DATABASE_URL = "postgresql://admin:SuperSecret123@prod-db:5432/shop"
API_KEY = "sk-live-9f8e7d6c5b4a"
DEBUG = True


def get_database_url() -> str:
    return DATABASE_URL


def get_api_key() -> str:
    return API_KEY


def is_debug() -> bool:
    return DEBUG
