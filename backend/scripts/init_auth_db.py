"""Create only the Day 1 auth tables. Run from backend/: python -m scripts.init_auth_db."""

from app import models  # Register model metadata before creating tables.
from app.database import Base, get_engine


if __name__ == "__main__":
    Base.metadata.create_all(get_engine())
    print("Day 1 authentication tables are ready.")
