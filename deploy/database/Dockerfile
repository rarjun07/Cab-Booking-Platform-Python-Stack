# Build PostGIS on the official multi-architecture PostgreSQL base. The upstream
# postgis/postgis image currently publishes amd64 only; this also runs on Apple ARM.
FROM postgres:17-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-17-postgis-3 postgresql-17-postgis-3-scripts \
    && rm -rf /var/lib/apt/lists/*
COPY init-app.sh /docker-entrypoint-initdb.d/10-init-app.sh
