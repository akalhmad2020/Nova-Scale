from types import TracebackType
from typing import Protocol

from app.modules.packages.application.ports.package_repository import (
    PackageRepository,
)
from app.modules.packages.infrastructure.models.package import Package
from app.modules.shipments.application.ports.shipment_repository import (
    ShipmentRepository,
)


class UnitOfWork(Protocol):
    @property
    def packages(self) -> PackageRepository: ...

    @property
    def shipments(self) -> ShipmentRepository: ...

    async def __aenter__(self) -> "UnitOfWork": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def flush(self) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def refresh(
        self,
        package: Package,
    ) -> None: ...
