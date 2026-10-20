"""Container readiness: migration head, real SQL and shared Redis, plus HTTP for API."""
import sys
from urllib.request import urlopen

from alembic.config import Config
from alembic.script import ScriptDirectory
from redis import Redis
from sqlalchemy import text

from app.config import get_settings
from app.database import get_engine


def main():
    try:
        expected = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
        with get_engine().connect() as db:
            if db.scalar(text("SELECT version_num FROM alembic_version")) != expected:
                return 1
            db.scalar(text("SELECT postgis_version()"))
        with Redis.from_url(get_settings().redis_url.get_secret_value(),
                            socket_connect_timeout=2, socket_timeout=2) as cache:
            if not cache.ping():
                return 1
        if "--api" in sys.argv:
            with urlopen("http://127.0.0.1:8000/api/health", timeout=2) as response:
                if response.status != 200:
                    return 1
        return 0
    except Exception:
        # Health output must not reveal connection strings or provider details.
        return 1


if __name__ == "__main__":
    sys.exit(main())
