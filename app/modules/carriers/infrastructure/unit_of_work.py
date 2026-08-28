from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.carriers.infrastructure.models.carrier import Carrier
from app.modules.carriers.infrastructure.models.carrier_service import (
    CarrierService,
)
from app.modules.carriers.infrastructure.repositories.carrier_repository import (
    CarrierRepository,
)
from app.modules.carriers.infrastructure.repositories.carrier_service_repository import (
    CarrierServiceRepository,
)


class SQLAlchemyUnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

        self.carriers: CarrierRepository
        self.carrier_services: CarrierServiceRepository

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        self._session = self._session_factory()

        self.carriers = CarrierRepository(self._session)
        self.carrier_services = CarrierServiceRepository(self._session)

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
        model: Carrier | CarrierService,
    ) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")

        await self._session.refresh(model)
