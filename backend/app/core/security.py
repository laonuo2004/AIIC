import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt

from app.core.config import get_settings


def _password_bytes(password: str) -> bytes:
    return hashlib.sha256(password.encode("utf-8")).hexdigest().encode("ascii")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(_password_bytes(password), password_hash.encode("utf-8"))


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    key = get_settings().secret_key.encode("utf-8")
    return hmac.new(key, token.encode("utf-8"), hashlib.sha256).hexdigest()


def session_expiry() -> datetime:
    minutes = get_settings().access_token_expire_minutes
    return datetime.now(UTC) + timedelta(minutes=minutes)
