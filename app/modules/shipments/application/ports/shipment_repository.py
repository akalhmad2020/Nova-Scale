from typing import Protocol
from uuid import UUID

from app.modules.shipments.infrastructure.models.shipment import Shipment


class ShipmentRepository(Protocol):
    async def get_by_id_and_tenant(
        self,
        shipment_id: UUID,
        tenant_id: UUID,
    ) -> Shipment | None: ...

    async def get_by_tracking_number_and_tenant(
        self,
        tracking_number: str,
        tenant_id: UUID,
    ) -> Shipment | None: ...

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[Shipment]: ...

    def add(
        self,
        shipment: Shipment,
    ) -> None: ...
