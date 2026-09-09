from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.ai.application.agent.shipment_summary_models import (
    ShipmentEventSummary,
    ShipmentSummaryContext,
)
from app.ai.application.agent.shipment_summary_tool import ShipmentSummaryTool
from app.ai.application.services.analyze_shipment import AnalyzeShipmentService
from app.ai.application.services.analyze_shipment_operations import (
    AnalyzeShipmentOperationsService,
)


@pytest.mark.asyncio
async def test_analyze_shipment_uses_real_shipment_summary_context() -> None:
    tenant_id = uuid4()
    shipment_id = uuid4()

    now = datetime.now(UTC)

    latest_event = ShipmentEventSummary(
        id=uuid4(),
        event_type="picked_up",
        status="in_transit",
        location_id=uuid4(),
        description="Shipment picked up from origin",
        occurred_at=now - timedelta(hours=30),
        metadata=None,
    )

    context = ShipmentSummaryContext(
        shipment_id=shipment_id,
        tenant_id=tenant_id,
        tracking_number="NS-OPS-001",
        reference="OPS-REF-001",
        status="in_transit",
        service_type="express",
        description="Operational shipment",
        weight=Decimal("10.000"),
        weight_unit="kg",
        notes=None,
        customer_id=uuid4(),
        origin_location_id=uuid4(),
        destination_location_id=uuid4(),
        event_count=1,
        latest_event=latest_event,
        events=(latest_event,),
    )

    shipment_summary_tool = AsyncMock(
        spec=ShipmentSummaryTool,
    )
    shipment_summary_tool.execute.return_value = context

    service = AnalyzeShipmentService(
        shipment_summary_tool=shipment_summary_tool,
        analyze_operations_service=AnalyzeShipmentOperationsService(
            stale_in_transit_after=timedelta(hours=24),
        ),
    )

    result = await service.execute(
        tenant_id=tenant_id,
        shipment_id=shipment_id,
    )

    shipment_summary_tool.execute.assert_awaited_once_with(
        tenant_id=tenant_id,
        shipment_id=shipment_id,
    )

    assert result.has_issues is True

    codes = {issue.code for issue in result.issues}

    assert "stale_in_transit" in codes
    assert result.highest_severity == "warning"


@pytest.mark.asyncio
async def test_analyze_shipment_returns_clean_analysis_for_healthy_shipment() -> None:
    tenant_id = uuid4()
    shipment_id = uuid4()

    now = datetime.now(UTC)

    latest_event = ShipmentEventSummary(
        id=uuid4(),
        event_type="arrived_at_location",
        status="in_transit",
        location_id=uuid4(),
        description="Shipment arrived at regional hub",
        occurred_at=now,
        metadata=None,
    )

    context = ShipmentSummaryContext(
        shipment_id=shipment_id,
        tenant_id=tenant_id,
        tracking_number="NS-OPS-HEALTHY",
        reference=None,
        status="in_transit",
        service_type="standard",
        description=None,
        weight=Decimal("5.000"),
        weight_unit="kg",
        notes=None,
        customer_id=uuid4(),
        origin_location_id=uuid4(),
        destination_location_id=uuid4(),
        event_count=1,
        latest_event=latest_event,
        events=(latest_event,),
    )

    shipment_summary_tool = AsyncMock(
        spec=ShipmentSummaryTool,
    )
    shipment_summary_tool.execute.return_value = context

    service = AnalyzeShipmentService(
        shipment_summary_tool=shipment_summary_tool,
        analyze_operations_service=AnalyzeShipmentOperationsService(),
    )

    result = await service.execute(
        tenant_id=tenant_id,
        shipment_id=shipment_id,
    )

    assert result.issues == ()
    assert result.has_issues is False
    assert result.highest_severity == "info"
