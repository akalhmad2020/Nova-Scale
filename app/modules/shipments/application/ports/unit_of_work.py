from types import TracebackType
from typing import Protocol

from app.modules.customers.application.ports.customer_repository import (
    CustomerRepository,
)
from app.modules.locations.application.ports.location_repository import (
    LocationRepository,
)
from app.modules.shipments.application.ports.shipment_repository import (
    ShipmentRepository,
)
from app.modules.shipments.infrastructure.models.shipment import Shipment


class UnitOfWork(Protocol):
    @property
    def shipments(self) -> ShipmentRepository: ...

    @property
    def customers(self) -> CustomerRepository: ...

    @property
    def locations(self) -> LocationRepository: ...

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
        shipment: Shipment,
    ) -> None: ...
