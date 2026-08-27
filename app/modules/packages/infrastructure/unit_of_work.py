from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.packages.infrastructure.models.package import Package
from app.modules.packages.infrastructure.repositories.package_repository import (
    PackageRepository,
)
from app.modules.shipments.infrastructure.repositories.shipment_repository import (
    ShipmentRepository,
)


class SQLAlchemyUnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

        self.packages: PackageRepository
        self.shipments: ShipmentRepository

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        self._session = self._session_factory()

        self.packages = PackageRepository(self._session)
        self.shipments = ShipmentRepository(self._session)

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
        package: Package,
    ) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")

        await self._session.refresh(package)
