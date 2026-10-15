"""Create dedicated local databases and ignored settings, without changing existing roles."""

import getpass
import os
from pathlib import Path
import secrets

import psycopg
from psycopg import sql


def main():
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        raise SystemExit("backend/.env already exists; keep it and configure PostgreSQL manually.")
    role = "cab_booking_app"
    databases = ["cab_booking_dev", "cab_booking_test"]
    password = secrets.token_urlsafe(32)
    jwt_secret = secrets.token_urlsafe(48)
    with psycopg.connect(host="127.0.0.1", dbname="postgres", user=getpass.getuser(),
                         connect_timeout=5, autocommit=True) as conn:
        if conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [role]).fetchone():
            raise SystemExit("Project role already exists; configure backend/.env manually. No changes made.")
        for name in databases:
            if conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", [name]).fetchone():
                raise SystemExit("A project database already exists; configure manually. No changes made.")
        # Save generated configuration before database changes, so it can be recovered if setup stops.
        with open(env_path, "x", opener=lambda path, flags: os.open(path, flags, 0o600)) as env:
            env.write(
                f"DATABASE_URL=postgresql+psycopg://{role}:{password}@127.0.0.1:5432/{databases[0]}\n"
                f"TEST_DATABASE_URL=postgresql+psycopg://{role}:{password}@127.0.0.1:5432/{databases[1]}\n"
                f"JWT_SECRET={jwt_secret}\nCOOKIE_SECURE=false\nACCESS_TOKEN_MINUTES=30\n"
            )
        conn.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE").format(
            sql.Identifier(role), sql.Literal(password)))
        for name in databases:
            conn.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(sql.Identifier(name), sql.Identifier(role)))
    print("Created dedicated development/test databases and backend/.env. Credentials were not printed.")


if __name__ == "__main__":
    main()
