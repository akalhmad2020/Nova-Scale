from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.saas.infrastructure.repository import SQLAlchemySubscriptionRepository


class SQLAlchemySubscriptionUnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._subscriptions: SQLAlchemySubscriptionRepository | None = None

    async def __aenter__(self) -> "SQLAlchemySubscriptionUnitOfWork":
        self._session = self._session_factory()
        self._subscriptions = SQLAlchemySubscriptionRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        session = self._session
        self._subscriptions = None

        if session is None:
            return

        try:
            if exc_type is not None:
                await session.rollback()
        finally:
            await session.close()
            self._session = None

    @property
    def subscriptions(self) -> SQLAlchemySubscriptionRepository:
        if self._subscriptions is None:
            raise RuntimeError("Unit of work is not active")
        return self._subscriptions

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")
        await self._session.commit()

    async def rollback(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")
        await self._session.rollback()

    async def refresh(self, instance: object) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")

        await self._session.refresh(instance)
