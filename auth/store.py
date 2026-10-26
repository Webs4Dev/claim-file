import hashlib
import re
import secrets
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from auth.passwords import hash_password, validate_password
from state.store import redis_client

Role = Literal["claimant", "reviewer"]

SESSION_TTL_SECONDS = 7 * 24 * 60 * 60

# Limits per 15-minute window. Attempts are counted per email *and* IP, so
# someone elsewhere cannot lock a victim out by guessing their email; the
# per-IP failure cap slows one client trying many emails.
LOGIN_ATTEMPT_LIMIT = 5
LOGIN_IP_FAILURE_LIMIT = 30
LOGIN_WINDOW_SECONDS = 15 * 60

# Deliberately loose: real validation would be a confirmation email.
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class User(BaseModel):
    user_id: str = Field(default_factory=lambda: str(uuid4()))
    email: str
    name: str
    role: Role
    password_hash: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def public(self) -> dict:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
        }


def normalize_email(email: str) -> str:
    return email.strip().lower()


def load_user(user_id: str) -> User | None:
    data = redis_client.get(f"user:{user_id}")
    return User.model_validate_json(data) if data else None


def find_user_by_email(email: str) -> User | None:
    user_id = redis_client.get(f"user_email:{normalize_email(email)}")
    return load_user(user_id) if user_id else None


def create_user(email: str, name: str, password: str, role: Role) -> User:
    """Raises ValueError on invalid input or an email already in use."""
    email = normalize_email(email)
    name = name.strip()

    if not EMAIL_PATTERN.match(email):
        raise ValueError("Enter a valid email address.")

    if not name:
        raise ValueError("Name cannot be empty.")

    validate_password(password)

    user = User(
        email=email,
        name=name,
        role=role,
        password_hash=hash_password(password),
    )

    # Claim the email first (atomic NX) so two simultaneous sign-ups with
    # the same address cannot both succeed.
    if not redis_client.set(f"user_email:{email}", user.user_id, nx=True):
        raise ValueError("An account with this email already exists.")

    redis_client.set(f"user:{user.user_id}", user.model_dump_json())

    return user


def _session_key(token: str) -> str:
    # Only a hash of the token is stored, so a Redis dump cannot be
    # replayed as a login cookie.
    digest = hashlib.sha256(token.encode()).hexdigest()
    return f"session:{digest}"


def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    redis_client.set(_session_key(token), user_id, ex=SESSION_TTL_SECONDS)
    return token


def user_for_session(token: str | None) -> User | None:
    if not token:
        return None

    user_id = redis_client.get(_session_key(token))
    return load_user(user_id) if user_id else None


def delete_session(token: str | None) -> None:
    if token:
        redis_client.delete(_session_key(token))


def _attempt_key(email: str, ip: str) -> str:
    return f"login_attempts:{normalize_email(email)}:{ip}"


def _increment(key: str) -> int:
    pipeline = redis_client.pipeline()
    pipeline.incr(key)
    # The window starts at the first hit and is not extended.
    pipeline.expire(key, LOGIN_WINDOW_SECONDS, nx=True)
    count, _ = pipeline.execute()
    return count


def reserve_login_attempt(email: str, ip: str) -> bool:
    """Count this attempt before checking the password.

    INCR is atomic, so parallel requests cannot all pass the check.
    """
    attempts = _increment(_attempt_key(email, ip))
    ip_failures = int(redis_client.get(f"login_fail_ip:{ip}") or 0)
    return attempts <= LOGIN_ATTEMPT_LIMIT and ip_failures < LOGIN_IP_FAILURE_LIMIT


def record_login_failure(ip: str) -> None:
    _increment(f"login_fail_ip:{ip}")


def clear_login_attempts(email: str, ip: str) -> None:
    redis_client.delete(_attempt_key(email, ip))
