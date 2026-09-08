#!/usr/bin/env bash

set -euo pipefail


TEST_DATABASE_URL="$(
    uv run python -c "
from app.core.config import get_settings
from sqlalchemy.engine import make_url

url = make_url(get_settings().database_url).set(
    host='localhost',
    database='novascale_test',
)

print(url.render_as_string(hide_password=False))
"
)"


TEST_MIGRATION_DATABASE_URL="$(
    uv run python -c "
from app.core.config import get_settings
from sqlalchemy.engine import make_url

url = make_url(get_settings().migration_database_url).set(
    host='localhost',
    database='novascale_test',
)

print(url.render_as_string(hide_password=False))
"
)"


export TEST_DATABASE_URL
export DATABASE_URL="$TEST_DATABASE_URL"
export MIGRATION_DATABASE_URL="$TEST_MIGRATION_DATABASE_URL"

export APP_ENV="test"
export AI_OLLAMA_BASE_URL="http://localhost:11434"


./scripts/setup-test-database.sh

uv run alembic upgrade head

./scripts/setup-test-database.sh


exec uv run pytest -m integration -q "$@"