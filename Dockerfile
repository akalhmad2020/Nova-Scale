# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:0.12.5 AS uv

FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock ./

FROM base AS development
RUN uv sync --locked --all-groups --no-install-project
COPY . .
CMD ["fastapi", "dev", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS production-builder
RUN uv sync --locked --no-dev --no-install-project

FROM python:3.13-slim AS production
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app
RUN groupadd --system novascale \
    && useradd --system --gid novascale --home-dir /nonexistent --no-create-home novascale
COPY --from=production-builder /app/.venv /app/.venv
COPY app /app/app
COPY migrations /app/migrations
COPY alembic.ini /app/alembic.ini
USER novascale
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3)"]
CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
