from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.locations.infrastructure.models.location import Location
from app.modules.locations.infrastructure.repositories.location_repository import (
    LocationRepository,
)


class SQLAlchemyUnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self.locations: LocationRepository

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        self._session = self._session_factory()

        self.locations = LocationRepository(self._session)

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
                await self.rollback()
        finally:
            await self._session.close()
            self._session = None

    async def flush(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")

        await self._session.flush()

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")

        await self._session.commit()

    async def rollback(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")

        await self._session.rollback()

    async def refresh(
        self,
        location: Location,
    ) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")

        await self._session.refresh(location)
