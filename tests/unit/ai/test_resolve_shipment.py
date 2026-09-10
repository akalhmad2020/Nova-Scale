from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.ai.application.agent.shipment_resolution_exceptions import (
    ShipmentIdentifierAmbiguousError,
)
from app.ai.application.services.resolve_shipment import ResolveShipmentService
from app.modules.shipments.application.exceptions import ShipmentNotFoundError
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
    tracking_number: str,
    reference: str | None,
) -> Shipment:
    shipment = Shipment(
        tenant_id=tenant_id,
        customer_id=uuid4(),
        origin_location_id=uuid4(),
        destination_location_id=uuid4(),
        tracking_number=tracking_number,
        reference=reference,
        status=ShipmentStatus.IN_TRANSIT,
        service_type=ServiceType.EXPRESS,
        description="Shipment resolver test",
        weight=Decimal("10.000"),
        weight_unit=WeightUnit.KG,
        notes=None,
    )

    shipment.id = uuid4()

    return shipment


@pytest.mark.asyncio
async def test_resolve_shipment_by_uuid() -> None:
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="RESOLVE-UUID-001",
        reference="REF-UUID-001",
    )

    uow = FakeUnitOfWork()
    uow.shipments.add(shipment)

    service = ResolveShipmentService(
        unit_of_work=uow,
    )

    result = await service.execute(
        tenant_id=tenant_id,
        identifier=str(shipment.id),
    )

    assert result.shipment_id == shipment.id
    assert result.identifier == str(shipment.id)
    assert result.identifier_kind == "uuid"


@pytest.mark.asyncio
async def test_resolve_shipment_by_tracking_number() -> None:
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="NS-TRACK-001",
        reference="CUSTOMER-REF-001",
    )

    uow = FakeUnitOfWork()
    uow.shipments.add(shipment)

    service = ResolveShipmentService(
        unit_of_work=uow,
    )

    result = await service.execute(
        tenant_id=tenant_id,
        identifier="NS-TRACK-001",
    )

    assert result.shipment_id == shipment.id
    assert result.identifier == "NS-TRACK-001"
    assert result.identifier_kind == "tracking_number"


@pytest.mark.asyncio
async def test_resolve_shipment_by_reference() -> None:
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="NS-TRACK-002",
        reference="CUSTOMER-REF-002",
    )

    uow = FakeUnitOfWork()
    uow.shipments.add(shipment)

    service = ResolveShipmentService(
        unit_of_work=uow,
    )

    result = await service.execute(
        tenant_id=tenant_id,
        identifier="CUSTOMER-REF-002",
    )

    assert result.shipment_id == shipment.id
    assert result.identifier == "CUSTOMER-REF-002"
    assert result.identifier_kind == "reference"


@pytest.mark.asyncio
async def test_resolve_shipment_prefers_tracking_number_over_reference() -> None:
    tenant_id = uuid4()

    tracking_match = make_shipment(
        tenant_id=tenant_id,
        tracking_number="SHARED-IDENTIFIER",
        reference="TRACKING-REF",
    )

    reference_match = make_shipment(
        tenant_id=tenant_id,
        tracking_number="OTHER-TRACKING",
        reference="SHARED-IDENTIFIER",
    )

    uow = FakeUnitOfWork()
    uow.shipments.add(tracking_match)
    uow.shipments.add(reference_match)

    service = ResolveShipmentService(
        unit_of_work=uow,
    )

    result = await service.execute(
        tenant_id=tenant_id,
        identifier="SHARED-IDENTIFIER",
    )

    assert result.shipment_id == tracking_match.id
    assert result.identifier_kind == "tracking_number"


@pytest.mark.asyncio
async def test_resolve_shipment_rejects_ambiguous_reference() -> None:
    tenant_id = uuid4()

    first_shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="NS-AMBIGUOUS-001",
        reference="CUSTOMER-ORDER-100",
    )

    second_shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="NS-AMBIGUOUS-002",
        reference="CUSTOMER-ORDER-100",
    )

    uow = FakeUnitOfWork()
    uow.shipments.add(first_shipment)
    uow.shipments.add(second_shipment)

    service = ResolveShipmentService(
        unit_of_work=uow,
    )

    with pytest.raises(ShipmentIdentifierAmbiguousError):
        await service.execute(
            tenant_id=tenant_id,
            identifier="CUSTOMER-ORDER-100",
        )


@pytest.mark.asyncio
async def test_resolve_shipment_rejects_unknown_identifier() -> None:
    service = ResolveShipmentService(
        unit_of_work=FakeUnitOfWork(),
    )

    with pytest.raises(ShipmentNotFoundError):
        await service.execute(
            tenant_id=uuid4(),
            identifier="UNKNOWN-SHIPMENT",
        )


@pytest.mark.asyncio
async def test_resolve_shipment_rejects_blank_identifier() -> None:
    service = ResolveShipmentService(
        unit_of_work=FakeUnitOfWork(),
    )

    with pytest.raises(ShipmentNotFoundError):
        await service.execute(
            tenant_id=uuid4(),
            identifier="   ",
        )


@pytest.mark.asyncio
async def test_resolve_shipment_enforces_tenant_isolation() -> None:
    owner_tenant_id = uuid4()
    foreign_tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=owner_tenant_id,
        tracking_number="TENANT-ISOLATED-001",
        reference="TENANT-REF-001",
    )

    uow = FakeUnitOfWork()
    uow.shipments.add(shipment)

    service = ResolveShipmentService(
        unit_of_work=uow,
    )

    with pytest.raises(ShipmentNotFoundError):
        await service.execute(
            tenant_id=foreign_tenant_id,
            identifier="TENANT-ISOLATED-001",
        )


@pytest.mark.asyncio
async def test_resolve_shipment_ignores_soft_deleted_shipment() -> None:
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="DELETED-TRACKING-001",
        reference="DELETED-REF-001",
    )

    shipment.deleted_at = datetime.now(UTC)

    uow = FakeUnitOfWork()
    uow.shipments.add(shipment)

    service = ResolveShipmentService(
        unit_of_work=uow,
    )

    with pytest.raises(ShipmentNotFoundError):
        await service.execute(
            tenant_id=tenant_id,
            identifier="DELETED-TRACKING-001",
        )
