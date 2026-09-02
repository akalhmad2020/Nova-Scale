from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.ai.application.agent.context import AgentContext
from app.ai.application.agent.get_shipment_tool import GetShipmentTool
from app.modules.shipments.application.exceptions import ShipmentNotFoundError
from app.modules.shipments.application.use_cases.get_shipment import GetShipment
from app.modules.shipments.domain.enums import (
    ServiceType,
    ShipmentStatus,
    WeightUnit,
)
from app.modules.shipments.infrastructure.models.shipment import Shipment
from tests.unit.shipments.fakes import FakeUnitOfWork


def make_shipment(
    *,
    tenant_id: UUID,
) -> Shipment:
    shipment = Shipment(
        tenant_id=tenant_id,
        customer_id=uuid4(),
        origin_location_id=uuid4(),
        destination_location_id=uuid4(),
        tracking_number="SHIP-001",
        reference="ORDER-100",
        status=ShipmentStatus.DRAFT,
        service_type=ServiceType.STANDARD,
        description="Electronics shipment",
        weight=Decimal("12.500"),
        weight_unit=WeightUnit.KG,
        notes="Handle with care",
    )
    shipment.id = uuid4()

    return shipment


@pytest.mark.asyncio
async def test_get_shipment_tool_returns_agent_friendly_result() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    uow.shipments.add(shipment)

    tool = GetShipmentTool(
        get_shipment=GetShipment(uow),
    )

    result = await tool.execute(
        context=AgentContext(
            tenant_id=tenant_id,
        ),
        shipment_id=shipment.id,
    )

    assert result.id == shipment.id
    assert result.tracking_number == "SHIP-001"
    assert result.reference == "ORDER-100"
    assert result.status == "draft"
    assert result.service_type == "standard"
    assert result.description == "Electronics shipment"
    assert result.weight == "12.500"
    assert result.weight_unit == "kg"
    assert result.notes == "Handle with care"


@pytest.mark.asyncio
async def test_get_shipment_tool_preserves_tenant_isolation() -> None:
    uow = FakeUnitOfWork()

    shipment = make_shipment(
        tenant_id=uuid4(),
    )

    uow.shipments.add(shipment)

    tool = GetShipmentTool(
        get_shipment=GetShipment(uow),
    )

    with pytest.raises(ShipmentNotFoundError):
        await tool.execute(
            context=AgentContext(
                tenant_id=uuid4(),
            ),
            shipment_id=shipment.id,
        )
