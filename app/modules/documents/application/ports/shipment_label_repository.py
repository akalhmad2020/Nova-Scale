from typing import Protocol
from uuid import UUID

from app.modules.documents.infrastructure.models.shipment_label import ShipmentLabel


class ShipmentLabelRepository(Protocol):
    async def get_by_id_and_tenant(
        self,
        shipment_label_id: UUID,
        tenant_id: UUID,
    ) -> ShipmentLabel | None: ...

    async def list_by_shipment(
        self,
        shipment_id: UUID,
        tenant_id: UUID,
    ) -> list[ShipmentLabel]: ...

    def add(
        self,
        shipment_label: ShipmentLabel,
    ) -> None: ...
