"""Generate independent, owner-only Docker credentials; never print secrets."""
import os
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parents[1]


def main():
    paths = [ROOT / ".env.database", ROOT / ".env.compose"]
    if any(path.exists() or path.is_symlink() for path in paths):
        raise SystemExit("Compose configuration already exists. Keep it: changing a password does not update an existing database volume.")
    password = secrets.token_hex(32)
    database = f"POSTGRES_USER=postgres\nPOSTGRES_PASSWORD={secrets.token_hex(32)}\nPOSTGRES_DB=postgres\nAPP_DB_PASSWORD={password}\n"
    app = (f"DATABASE_URL=postgresql+psycopg://cab_app:{password}@database:5432/cab_booking\n"
           f"JWT_SECRET={secrets.token_urlsafe(48)}\nCOOKIE_SECURE=false\n"
           'ALLOWED_ORIGINS=["http://127.0.0.1:8080","http://localhost:8080"]\n'
           "REDIS_URL=redis://redis:6379/0\nRECEIPT_EMAIL_ENABLED=false\n"
           "OSRM_BASE_URL=https://router.project-osrm.org\n")
    # O_EXCL rejects overwrite/symlink races, and 0600 applies from first write.
    for path, content in zip(paths, [database, app], strict=True):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as output:
            output.write(content)
    print("Created .env.database and .env.compose (0600). No existing development settings changed.")


if __name__ == "__main__":
    main()
