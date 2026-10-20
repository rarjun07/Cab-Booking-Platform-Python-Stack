#!/bin/sh
# Sourced by the official entrypoint only on a NEW volume, as the administrator.
set -eu
psql --username "$POSTGRES_USER" --dbname postgres --set ON_ERROR_STOP=1 \
    --set app_password="$APP_DB_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE cab_app LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE', :'app_password') \gexec
CREATE DATABASE cab_booking OWNER cab_app;
\connect cab_booking
CREATE EXTENSION postgis;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SQL
