from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.auth import AUDIENCE, COOKIE_NAME, ISSUER, password_hasher
from app.config import Settings, get_settings
from app.models import User


def test_register_persists_only_hash_and_sets_private_cookie(client, db, account):
    response = client.post("/api/auth/register", json=account)
    assert response.status_code == 201
    assert set(response.json()) == {"id", "name", "email", "role"}
    stored = db.scalar(select(User).where(User.email == account["email"]))
    assert stored.password_hash.startswith("$argon2id$")
    assert password_hasher.verify(account["password"], stored.password_hash)
    assert account["password"] not in response.text
    assert response.headers["cache-control"] == "no-store"
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "path=/api" in cookie
    assert client.get("/api/auth/me").json()["id"] == str(stored.id)
    assert client.post("/api/auth/session", json={}).status_code == 200


def test_login_normalizes_email_and_restores_session(client, account):
    client.post("/api/auth/register", json=account)
    client.post("/api/auth/logout")
    response = client.post("/api/auth/login", json={"email": account["email"].upper(), "password": account["password"]})
    assert response.status_code == 200
    assert client.get("/api/auth/me").json()["email"] == account["email"]


def test_duplicate_email_is_case_insensitive(client, account):
    assert client.post("/api/auth/register", json=account).status_code == 201
    account["email"] = account["email"].upper()
    assert client.post("/api/auth/register", json=account).status_code == 409


@pytest.mark.parametrize("email,password", [("rider@example.com", "wrong-password"), ("absent@example.com", "wrong-password")])
def test_login_rejects_bad_credentials_without_identifying_account(client, account, email, password):
    client.post("/api/auth/register", json=account)
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password."


@pytest.mark.parametrize("field,value", [("password", "x!abc"), ("email", "not-an-email"), ("role", "admin"), ("name", "   ")])
def test_invalid_registration_is_rejected_without_echoing_password(client, account, field, value):
    account[field] = value
    response = client.post("/api/auth/register", json=account)
    assert response.status_code == 422
    assert account["password"] not in response.text
    assert all("input" not in error for error in response.json()["detail"])


def test_missing_or_tampered_cookie_is_rejected(client, account):
    assert client.get("/api/auth/me").status_code == 401
    client.post("/api/auth/register", json=account)
    token = client.cookies.get(COOKIE_NAME)
    header, payload, signature = token.split(".")
    modified = ("A" if signature[0] != "A" else "B") + signature[1:]
    client.cookies.clear()
    client.cookies.set(COOKIE_NAME, f"{header}.{payload}.{modified}")
    assert client.get("/api/auth/me").status_code == 401


def test_expired_token_is_rejected(client, account):
    client.post("/api/auth/register", json=account)
    key = get_settings().jwt_secret.get_secret_value()
    claims = jwt.decode(client.cookies.get(COOKIE_NAME), key, algorithms=["HS256"], audience=AUDIENCE, issuer=ISSUER)
    claims["exp"] = datetime.now(timezone.utc) - timedelta(seconds=10)
    client.cookies.clear()
    client.cookies.set(COOKIE_NAME, jwt.encode(claims, key, algorithm="HS256"))
    assert client.get("/api/auth/me").status_code == 401


def test_signed_token_without_database_session_is_rejected(client):
    now = datetime.now(timezone.utc)
    token = jwt.encode({"sub": str(uuid4()), "jti": str(uuid4()), "iat": now,
                        "exp": now + timedelta(minutes=5), "iss": ISSUER, "aud": AUDIENCE},
                       get_settings().jwt_secret.get_secret_value(), algorithm="HS256")
    client.cookies.set(COOKIE_NAME, token)
    assert client.get("/api/auth/me").status_code == 401


@pytest.mark.parametrize("claim,value", [("iss", "another-api"), ("aud", "another-app"), ("sub", "invalid-uuid"), ("jti", None)])
def test_wrong_or_missing_token_claims_are_rejected(client, account, claim, value):
    client.post("/api/auth/register", json=account)
    key = get_settings().jwt_secret.get_secret_value()
    claims = jwt.decode(client.cookies.get(COOKIE_NAME), key, algorithms=["HS256"], audience=AUDIENCE, issuer=ISSUER)
    if value is None:
        del claims[claim]
    else:
        claims[claim] = value
    client.cookies.clear()
    client.cookies.set(COOKIE_NAME, jwt.encode(claims, key, algorithm="HS256"))
    assert client.get("/api/auth/me").status_code == 401


def test_logout_revokes_token_and_clears_cookie(client, account):
    client.post("/api/auth/register", json=account)
    old_token = client.cookies.get(COOKIE_NAME)
    response = client.post("/api/auth/logout")
    assert response.status_code == 204
    assert "max-age=0" in response.headers["set-cookie"].lower()
    assert client.get("/api/auth/me").status_code == 401
    client.cookies.set(COOKIE_NAME, old_token)
    assert client.get("/api/auth/me").status_code == 401


@pytest.mark.parametrize("path", ["register", "login", "logout", "session"])
def test_cross_origin_mutations_are_rejected(client, path, account):
    response = client.post(f"/api/auth/{path}", json=account, headers={"Origin": "https://untrusted.example"})
    assert response.status_code == 403


def test_missing_origin_is_rejected(client, account):
    del client.headers["origin"]
    assert client.post("/api/auth/register", json=account).status_code == 403


def test_example_signing_secret_is_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="postgresql+psycopg://unused/unused",
                 jwt_secret="REPLACE_WITH_A_RANDOM_SECRET_AT_LEAST_48_CHARACTERS_LONG")


def test_secure_cookie_is_the_default():
    settings = Settings(_env_file=None, database_url="postgresql+psycopg://unused/unused",
                        jwt_secret="a" * 64)
    assert settings.cookie_secure is True
