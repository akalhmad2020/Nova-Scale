from types import TracebackType

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.shared.outbox.application.ports.repositories import (
    OutboxMessageRepository,
)
from app.shared.outbox.infrastructure.repositories.sqlalchemy import (
    SQLAlchemyOutboxMessageRepository,
)


class SQLAlchemyOutboxUnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self.messages: OutboxMessageRepository

    async def __aenter__(self) -> "SQLAlchemyOutboxUnitOfWork":
        self._session = self._session_factory()

        self.messages = SQLAlchemyOutboxMessageRepository(
            self._session,
        )

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session is None:
            return

        try:
            if exc_type is not None:
                await self._session.rollback()
        finally:
            await self._session.close()

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work has not been entered.")

        await self._session.commit()

    async def rollback(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work has not been entered.")

        await self._session.rollback()
