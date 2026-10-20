FROM python:3.14-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 XDG_CACHE_HOME=/tmp/cache
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 cab && useradd --uid 10001 --gid cab --create-home cab
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --requirement requirements.txt
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts/container_health.py ./scripts/container_health.py
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
