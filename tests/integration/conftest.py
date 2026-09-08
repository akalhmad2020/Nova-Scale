import os
from collections.abc import AsyncIterator, Awaitable, Callable
from uuid import UUID

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from tests.integration.rls import set_session_tenant_context

SetTenantContext = Callable[[UUID], Awaitable[None]]


def get_test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")

    if not database_url:
        raise RuntimeError("TEST_DATABASE_URL must be set when running integration tests.")

    parsed_url = make_url(database_url)
    database_name = parsed_url.database

    if database_name != "novascale_test":
        raise RuntimeError(
            f"Integration tests must use the 'novascale_test' database. Received: {database_name!r}"
        )

    return database_url


def configure_integration_environment() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")

    if not database_url:
        return

    parsed_url = make_url(database_url)
    database_name = parsed_url.database

    if database_name != "novascale_test":
        raise RuntimeError(
            f"Integration tests must use the 'novascale_test' database. Received: {database_name!r}"
        )

    os.environ["APP_ENV"] = "test"
    os.environ["DATABASE_URL"] = database_url


configure_integration_environment()


@pytest.fixture
async def test_engine() -> AsyncIterator[AsyncEngine]:
    database_url = get_test_database_url()

    engine = create_async_engine(
        database_url,
        poolclass=NullPool,
    )

    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def session_factory(
    test_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest.fixture
def set_tenant_context(
    db_session: AsyncSession,
) -> SetTenantContext:
    async def _set_tenant_context(tenant_id: UUID) -> None:
        await set_session_tenant_context(
            db_session,
            tenant_id,
        )

    return _set_tenant_context
