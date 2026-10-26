import bcrypt

# bcrypt only uses the first 72 bytes of a password and bcrypt 5 rejects
# longer input, so the limit is enforced (and explained) at registration.
MAX_PASSWORD_BYTES = 72
MIN_PASSWORD_LENGTH = 8

# Compared against when an email is unknown, so a failed login takes the
# same time whether or not the account exists.
_DUMMY_HASH = bcrypt.hashpw(b"timing-equaliser", bcrypt.gensalt()).decode()


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )

    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password must be at most {MAX_PASSWORD_BYTES} bytes."
        )


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    encoded = password.encode("utf-8")

    if password_hash is None or len(encoded) > MAX_PASSWORD_BYTES:
        bcrypt.checkpw(b"timing-equaliser", _DUMMY_HASH.encode())
        return False

    return bcrypt.checkpw(encoded, password_hash.encode())
