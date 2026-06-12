import bcrypt

_users: dict[str, str] = {}


def register(username: str, password: str) -> None:
    if username in _users:
        raise ValueError("username taken")
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    _users[username] = hashed.decode("utf-8")


def verify(username: str, password: str) -> bool:
    stored = _users.get(username)
    if stored is None:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), stored.encode("utf-8"))


def get_stored_credential(username: str) -> str:
    return _users[username]


def reset() -> None:
    _users.clear()
