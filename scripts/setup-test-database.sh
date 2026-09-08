#!/usr/bin/env bash

set -euo pipefail

TEST_DATABASE_NAME="novascale_test"

docker compose exec -T postgres sh -lc "
set -e

database_exists=\$(psql \
    -U \"\$POSTGRES_USER\" \
    -d postgres \
    -tAc \"SELECT 1 FROM pg_database WHERE datname = '$TEST_DATABASE_NAME'\")

if [ \"\$database_exists\" != \"1\" ]; then
    createdb \
        -U \"\$POSTGRES_USER\" \
        -O \"\$POSTGRES_USER\" \
        \"$TEST_DATABASE_NAME\"
fi

psql \
    -v ON_ERROR_STOP=1 \
    -U \"\$POSTGRES_USER\" \
    -d \"$TEST_DATABASE_NAME\" <<'SQL'

GRANT CONNECT
ON DATABASE novascale_test
TO novascale_app;

GRANT USAGE
ON SCHEMA public
TO novascale_app;

GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA public
TO novascale_app;

GRANT USAGE, SELECT
ON ALL SEQUENCES IN SCHEMA public
TO novascale_app;

ALTER DEFAULT PRIVILEGES
FOR ROLE novascale
IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLES
TO novascale_app;

ALTER DEFAULT PRIVILEGES
FOR ROLE novascale
IN SCHEMA public
GRANT USAGE, SELECT
ON SEQUENCES
TO novascale_app;

SQL
"