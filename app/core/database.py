from collections.abc import AsyncIterator

from sqlalchemy import event, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, SessionTransaction
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.tenant_context import get_current_tenant_id

settings = get_settings()


@event.listens_for(Session, "after_begin")
def _set_transaction_tenant_context(
    session: Session,
    transaction: SessionTransaction,
    connection: Connection,
) -> None:
    del session, transaction

    tenant_id = get_current_tenant_id()

    if tenant_id is None:
        return

    connection.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )


def create_engine() -> AsyncEngine:
    connect_args = {
        "timeout": settings.db_connect_timeout_seconds,
        "command_timeout": settings.db_command_timeout_seconds,
    }

    if settings.app_env == "test":
        return create_async_engine(
            settings.database_url,
            poolclass=NullPool,
            connect_args=connect_args,
        )

    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout_seconds,
        pool_recycle=settings.db_pool_recycle_seconds,
        connect_args=connect_args,
    )


engine: AsyncEngine = create_engine()

SessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session


async def dispose_engine() -> None:
    await engine.dispose()
