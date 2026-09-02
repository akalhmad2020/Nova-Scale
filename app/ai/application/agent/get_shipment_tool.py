from uuid import UUID

from app.ai.application.agent.context import AgentContext
from app.ai.application.agent.models import ShipmentToolResult
from app.modules.shipments.application.use_cases.get_shipment import (
    GetShipment,
    GetShipmentQuery,
)


class GetShipmentTool:
    def __init__(
        self,
        *,
        get_shipment: GetShipment,
    ) -> None:
        self._get_shipment = get_shipment

    async def execute(
        self,
        *,
        context: AgentContext,
        shipment_id: UUID,
    ) -> ShipmentToolResult:
        shipment = await self._get_shipment.execute(
            GetShipmentQuery(
                tenant_id=context.tenant_id,
                shipment_id=shipment_id,
            )
        )

        return ShipmentToolResult(
            id=shipment.id,
            tracking_number=shipment.tracking_number,
            reference=shipment.reference,
            status=shipment.status.value,
            service_type=shipment.service_type.value,
            description=shipment.description,
            weight=str(shipment.weight),
            weight_unit=shipment.weight_unit.value,
            notes=shipment.notes,
        )
