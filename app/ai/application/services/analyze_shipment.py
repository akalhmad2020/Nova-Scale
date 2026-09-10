from uuid import UUID

from app.ai.application.agent.shipment_operational_models import (
    ShipmentOperationalAnalysis,
)
from app.ai.application.agent.shipment_summary_tool import ShipmentSummaryTool
from app.ai.application.services.analyze_shipment_operations import (
    AnalyzeShipmentOperationsService,
)


class AnalyzeShipmentService:
    def __init__(
        self,
        *,
        shipment_summary_tool: ShipmentSummaryTool,
        analyze_operations_service: AnalyzeShipmentOperationsService,
    ) -> None:
        self._shipment_summary_tool = shipment_summary_tool
        self._analyze_operations_service = analyze_operations_service

    async def execute(
        self,
        *,
        tenant_id: UUID,
        shipment_id: UUID,
    ) -> ShipmentOperationalAnalysis:
        context = await self._shipment_summary_tool.execute(
            tenant_id=tenant_id,
            shipment_id=shipment_id,
        )

        return self._analyze_operations_service.execute(
            context=context,
        )
