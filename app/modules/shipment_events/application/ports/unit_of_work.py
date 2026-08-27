from types import TracebackType
from typing import Protocol

from app.modules.locations.application.ports.location_repository import (
    LocationRepository,
)
from app.modules.shipment_events.application.ports.shipment_event_repository import (
    ShipmentEventRepository,
)
from app.modules.shipment_events.infrastructure.models.shipment_event import (
    ShipmentEvent,
)
from app.modules.shipments.application.ports.shipment_repository import (
    ShipmentRepository,
)


class UnitOfWork(Protocol):
    @property
    def shipment_events(self) -> ShipmentEventRepository: ...

    @property
    def shipments(self) -> ShipmentRepository: ...

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
        event: ShipmentEvent,
    ) -> None: ...
