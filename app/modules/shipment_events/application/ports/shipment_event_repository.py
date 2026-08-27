from typing import Protocol
from uuid import UUID

from app.modules.shipment_events.infrastructure.models.shipment_event import (
    ShipmentEvent,
)


class ShipmentEventRepository(Protocol):
    async def list_by_shipment(
        self,
        shipment_id: UUID,
        tenant_id: UUID,
    ) -> list[ShipmentEvent]: ...

    def add(
        self,
        event: ShipmentEvent,
    ) -> None: ...
