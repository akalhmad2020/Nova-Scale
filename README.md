# NovaScale

Production-grade B2B shipping and logistics SaaS platform with a deterministic business core and a controlled evidence-driven AI layer.

## Bootstrap scope

This baseline intentionally contains only engineering/runtime foundations:

- FastAPI
- PostgreSQL
- SQLAlchemy 2.x async
- Alembic
- Docker / Docker Compose
- health and readiness probes
- Ruff, mypy, pytest
- GitHub Actions CI

Business modules begin with Identity and Multi-tenancy after this baseline passes its exit criteria.

## Prerequisites

- Git
- Docker + Docker Compose
- `uv` 0.12.x

## First-time bootstrap

Generate and commit the dependency lockfile before building images:

```bash
uv lock
uv sync --locked --all-groups
```

Create local environment configuration:

```bash
cp .env.example .env
```

Change the local PostgreSQL password in `.env`, and keep `.env` out of Git.

## Start locally with Docker

```bash
docker compose build
docker compose up -d postgres
docker compose run --rm backend alembic upgrade head
docker compose up -d backend
```

Check:

```text
http://localhost:8000/health
http://localhost:8000/health/live
http://localhost:8000/health/ready
http://localhost:8000/docs
```

Expected health responses:

```json
{"status":"ok"}
{"status":"ready"}
```

## Run quality checks locally

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy app tests
uv run pytest
```

For integration tests, make sure PostgreSQL is available and override `DATABASE_URL` so it points to the test database on `localhost`, then run:

```bash
uv run pytest -m integration
```

## Database migrations

Schema changes are performed only through Alembic.

```bash
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

Never use `Base.metadata.create_all()` as the project migration strategy.

## Git workflow

Initialize the repository only after `uv.lock` has been generated successfully:

```bash
git init
git branch -M main
git add .
git commit -m "chore: bootstrap NovaScale foundation"
```

Then create short-lived branches such as `feat/identity-auth`, `fix/tenant-isolation`, or `chore/docker`. Merge through pull requests only after CI passes and use Conventional Commits.
