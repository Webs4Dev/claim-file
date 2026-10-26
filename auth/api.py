from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from auth.passwords import verify_password
from auth.store import (
    SESSION_TTL_SECONDS,
    User,
    clear_login_attempts,
    create_session,
    create_user,
    delete_session,
    find_user_by_email,
    record_login_failure,
    reserve_login_attempt,
    user_for_session,
)
from config import COOKIE_SECURE

SESSION_COOKIE = "claimfile_session"

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str = Field(max_length=254)
    name: str = Field(max_length=100)
    password: str = Field(max_length=200)


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)


def client_ip(request: Request) -> str:
    # Direct peer address. Behind a reverse proxy this is the proxy, so a
    # deployment must derive the client IP from trusted forwarding headers.
    return request.client.host if request.client else "unknown"


def start_session(request: Request, response: Response, user: User) -> None:
    # Drop any session this browser already had before issuing a new one.
    delete_session(request.cookies.get(SESSION_COOKIE))
    set_session_cookie(response, user)


def set_session_cookie(response: Response, user: User) -> None:
    # httpOnly: page scripts cannot read the token. SameSite=Lax: other
    # sites cannot make the browser send it with their POST requests.
    response.set_cookie(
        SESSION_COOKIE,
        create_session(user.user_id),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/",
    )


def current_user(request: Request) -> User:
    user = user_for_session(request.cookies.get(SESSION_COOKIE))

    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to continue.")

    return user


def require_reviewer(user: User = Depends(current_user)) -> User:
    if user.role != "reviewer":
        raise HTTPException(
            status_code=403,
            detail="Only reviewers can do this.",
        )

    return user


@router.post("/register")
def register(body: RegisterRequest, request: Request, response: Response):
    # Public sign-up always creates a claimant. Reviewer accounts are made
    # with scripts/create_reviewer.py so nobody can promote themselves.
    try:
        user = create_user(body.email, body.name, body.password, "claimant")
    except ValueError as error:
        status = 409 if "already exists" in str(error) else 400
        raise HTTPException(status_code=status, detail=str(error)) from error

    start_session(request, response, user)
    return user.public()


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response):
    ip = client_ip(request)

    if not reserve_login_attempt(body.email, ip):
        raise HTTPException(
            status_code=429,
            detail="Too many sign-in attempts. Try again in 15 minutes.",
        )

    user = find_user_by_email(body.email)

    if not verify_password(body.password, user.password_hash if user else None):
        record_login_failure(ip)
        # Same message for unknown email and wrong password.
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    clear_login_attempts(body.email, ip)
    start_session(request, response, user)
    return user.public()


@router.post("/logout")
def logout(request: Request, response: Response):
    delete_session(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"status": "signed_out"}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user.public()
