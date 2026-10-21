"""Password hashing, signed cookies, and PostgreSQL session verification."""

from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import AuthSession, User
from app.schemas import LoginInput, RegisterInput, UserPublic, ProfileInput
from app import security

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
password_hasher = PasswordHash.recommended()
dummy_hash = password_hasher.hash("dummy-password-for-login-timing-only")
COOKIE_NAME = "cab_session"
ISSUER = "cab-booking-api"
AUDIENCE = "cab-booking-frontend"
DB = Annotated[Session, Depends(get_db)]


def check_origin(request: Request) -> None:
    """State-changing cookie requests must come from our configured app origins."""
    if request.headers.get("origin") not in get_settings().allowed_origins:
        raise HTTPException(403, "Request origin is not allowed.")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            get_settings().jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            issuer=ISSUER,
            audience=AUDIENCE,
            options={"require": ["exp", "iat", "sub", "jti", "iss", "aud"]},
        )
    except InvalidTokenError:
        raise HTTPException(401, "Please sign in again.") from None


def start_session(user: User, response: Response, db: Session) -> None:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.access_token_minutes)
    auth_session = AuthSession(user_id=user.id, expires_at=expires_at)
    db.add(auth_session)
    db.flush()
    token = jwt.encode(
        {"sub": str(user.id), "jti": str(auth_session.id), "iat": now,
         "exp": expires_at, "iss": ISSUER, "aud": AUDIENCE},
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    db.commit()
    response.set_cookie(
        COOKIE_NAME, token, max_age=settings.access_token_minutes * 60,
        httponly=True, secure=settings.cookie_secure, samesite="lax", path="/api",
    )
    response.headers["Cache-Control"] = "no-store"


def get_current_user(request: Request, response: Response, db: DB) -> User:
    user = user_from_token(request.cookies.get(COOKIE_NAME), db)
    response.headers["Cache-Control"] = "no-store"
    return user


def user_from_token(token: str | None, db: Session) -> User:
    """Shared HTTP/WebSocket validation; callers own a short database session."""
    if not token:
        raise HTTPException(401, "Please sign in to continue.")
    claims = decode_token(token)
    try:
        session_id, user_id = UUID(claims["jti"]), UUID(claims["sub"])
    except (ValueError, TypeError):
        raise HTTPException(401, "Please sign in again.") from None
    auth_session = db.get(AuthSession, session_id)
    if (auth_session is None or auth_session.user_id != user_id
            or auth_session.revoked_at is not None
            or auth_session.expires_at <= datetime.now(timezone.utc)):
        raise HTTPException(401, "Please sign in again.")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(401, "Please sign in again.")
    return user


@router.post("/register", response_model=UserPublic, status_code=201, dependencies=[Depends(check_origin)])
def register(data: RegisterInput, response: Response, db: DB):
    user = User(name=data.name, email=str(data.email), role=data.role,
                password_hash=password_hasher.hash(data.password))
    db.add(user)
    try:
        db.flush()
        start_session(user, response, db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An account with that email already exists.") from None
    return user


@router.post("/login", response_model=UserPublic, dependencies=[Depends(check_origin)])
def login(data: LoginInput, response: Response, db: DB):
    security.get_rate_limiter().check([("login_account", str(data.email), 10, 60)])
    user = db.scalar(select(User).where(User.email == str(data.email)))
    valid = password_hasher.verify(data.password, user.password_hash if user else dummy_hash)
    if user is None or not valid:
        raise HTTPException(401, "Incorrect email or password.")
    start_session(user, response, db)
    return user


@router.get("/me", response_model=UserPublic)
def current_user(user: Annotated[User, Depends(get_current_user)]):
    return user


@router.post("/profile", response_model=UserPublic, dependencies=[Depends(check_origin)])
def update_profile(data: ProfileInput, user: Annotated[User, Depends(get_current_user)], db: DB):
    # The session chooses the account; clients cannot submit an ID or role.
    current = db.scalar(select(User).where(User.id == user.id).with_for_update())
    current.name = data.name
    current.phone = data.phone
    current.profile_pic = str(data.profile_pic) if data.profile_pic else None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "That phone number is already in use.") from None
    db.refresh(current)
    return current


@router.post("/session", response_model=UserPublic, dependencies=[Depends(check_origin)])
def verify_session(user: Annotated[User, Depends(get_current_user)]):
    return user


@router.post("/logout", status_code=204, dependencies=[Depends(check_origin)])
def logout(request: Request, response: Response, db: DB):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        try:
            claims = decode_token(token)
            auth_session = db.get(AuthSession, UUID(claims["jti"]))
            if auth_session and str(auth_session.user_id) == claims["sub"]:
                auth_session.revoked_at = datetime.now(timezone.utc)
                db.commit()
        except (HTTPException, ValueError, TypeError):
            pass
    response.delete_cookie(COOKIE_NAME, path="/api",
                           secure=get_settings().cookie_secure, httponly=True, samesite="lax")
    response.headers["Cache-Control"] = "no-store"
