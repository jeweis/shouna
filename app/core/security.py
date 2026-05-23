from datetime import datetime, timedelta
from typing import Any, Union
import base64
import hashlib
import hmac
import os
import jwt
from app.core.config import settings

ALGORITHM = "HS256"
PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 260000
SALT_BYTES = 16


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        algorithm, iterations, salt, expected_hash = hashed_password.split("$")
        if algorithm != PASSWORD_HASH_ALGORITHM:
            return False
        actual_hash = _derive_password_hash(
            plain_password,
            base64.urlsafe_b64decode(salt.encode()),
            int(iterations),
        )
        return hmac.compare_digest(actual_hash, expected_hash)
    except (TypeError, ValueError):
        return False


def get_password_hash(password: str) -> str:
    salt = os.urandom(SALT_BYTES)
    encoded_salt = base64.urlsafe_b64encode(salt).decode()
    password_hash = _derive_password_hash(
        password,
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return f"{PASSWORD_HASH_ALGORITHM}${PASSWORD_HASH_ITERATIONS}${encoded_salt}${password_hash}"


def _derive_password_hash(password: str, salt: bytes, iterations: int) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return base64.urlsafe_b64encode(digest).decode()

def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
