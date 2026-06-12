# BROKEN: neither the signature nor the expiry of tokens is verified.
import time

import jwt

SECRET_KEY = "proofforge-dev-secret"
ALGORITHM = "HS256"


def create_token(username: str, expires_in_seconds: int = 3600) -> str:
    payload = {"sub": username, "exp": int(time.time()) + expires_in_seconds}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> str:
    payload = jwt.decode(token, options={"verify_signature": False})
    return payload["sub"]
