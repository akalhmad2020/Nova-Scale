#!/usr/bin/env bash

set -euo pipefail


: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${APP_DB_USER:?APP_DB_USER is required}"
: "${APP_DB_PASSWORD:?APP_DB_PASSWORD is required}"


psql \
    -v ON_ERROR_STOP=1 \
    --username "$POSTGRES_USER" \
    --dbname "$POSTGRES_DB" \
    --set=admin_user="$POSTGRES_USER" \
    --set=app_user="$APP_DB_USER" \
    --set=app_password="$APP_DB_PASSWORD" <<'SQL'

CREATE ROLE :"app_user"
    WITH
    LOGIN
    PASSWORD :'app_password'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOBYPASSRLS;

GRANT CONNECT
ON DATABASE :"DBNAME"
TO :"app_user";

GRANT USAGE
ON SCHEMA public
TO :"app_user";

GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA public
TO :"app_user";

GRANT USAGE, SELECT
ON ALL SEQUENCES IN SCHEMA public
TO :"app_user";

ALTER DEFAULT PRIVILEGES
FOR ROLE :"admin_user"
IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLES
TO :"app_user";

ALTER DEFAULT PRIVILEGES
FOR ROLE :"admin_user"
IN SCHEMA public
GRANT USAGE, SELECT
ON SEQUENCES
TO :"app_user";

SQL