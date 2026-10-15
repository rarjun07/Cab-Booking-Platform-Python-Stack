"""Compatibility entry point: database setup is now managed by Alembic."""

from pathlib import Path

from alembic import command
from alembic.config import Config


if __name__ == "__main__":
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    print("Database migrations are up to date.")
