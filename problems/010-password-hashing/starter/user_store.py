# BROKEN: passwords are stored and compared in plaintext.
_users: dict[str, str] = {}


def register(username: str, password: str) -> None:
    if username in _users:
        raise ValueError("username taken")
    _users[username] = password


def verify(username: str, password: str) -> bool:
    stored = _users.get(username)
    return stored == password


def get_stored_credential(username: str) -> str:
    return _users[username]


def reset() -> None:
    _users.clear()
