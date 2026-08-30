from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.audit.domain.enums import AuditActorType, AuditOutcome
from app.modules.shipments.application.exceptions import (
    InvalidShipmentStatusTransitionError,
    ShipmentNotFoundError,
)
from app.modules.shipments.application.use_cases.transition_shipment_status import (
    TransitionShipmentStatus,
    TransitionShipmentStatusCommand,
)
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
    status: ShipmentStatus,
) -> Shipment:
    shipment = Shipment(
        tenant_id=tenant_id,
        customer_id=uuid4(),
        origin_location_id=uuid4(),
        destination_location_id=uuid4(),
        tracking_number="SHIP-001",
        status=status,
        service_type=ServiceType.STANDARD,
        weight=Decimal("1.000"),
        weight_unit=WeightUnit.KG,
    )
    shipment.id = uuid4()

    return shipment


async def test_transition_shipment_status_updates_status() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()
    actor_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
        status=ShipmentStatus.DRAFT,
    )

    uow.shipments.add(shipment)

    result = await TransitionShipmentStatus(uow).execute(
        TransitionShipmentStatusCommand(
            tenant_id=tenant_id,
            actor_id=actor_id,
            shipment_id=shipment.id,
            target_status=ShipmentStatus.READY,
        )
    )

    assert result is shipment
    assert shipment.status == ShipmentStatus.READY

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.refreshed is True
    assert uow.rolled_back is False

    assert len(uow.audit_logs.items) == 1

    audit_log = uow.audit_logs.items[0]

    assert audit_log.tenant_id == tenant_id
    assert audit_log.actor_type == AuditActorType.USER
    assert audit_log.actor_id == actor_id
    assert audit_log.action == "shipment.status_changed"
    assert audit_log.resource_type == "shipment"
    assert audit_log.resource_id == shipment.id
    assert audit_log.outcome == AuditOutcome.SUCCESS

    assert audit_log.metadata_ == {
        "tracking_number": shipment.tracking_number,
        "previous_status": ShipmentStatus.DRAFT.value,
        "new_status": ShipmentStatus.READY.value,
    }

    assert audit_log.occurred_at is not None


async def test_transition_shipment_status_rejects_invalid_transition() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
        status=ShipmentStatus.DRAFT,
    )

    uow.shipments.add(shipment)

    with pytest.raises(InvalidShipmentStatusTransitionError):
        await TransitionShipmentStatus(uow).execute(
            TransitionShipmentStatusCommand(
                tenant_id=tenant_id,
                actor_id=uuid4(),
                shipment_id=shipment.id,
                target_status=ShipmentStatus.DELIVERED,
            )
        )

    assert shipment.status == ShipmentStatus.DRAFT
    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True
    assert uow.audit_logs.items == []


async def test_transition_shipment_status_rejects_unknown_shipment() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(ShipmentNotFoundError):
        await TransitionShipmentStatus(uow).execute(
            TransitionShipmentStatusCommand(
                tenant_id=uuid4(),
                actor_id=uuid4(),
                shipment_id=uuid4(),
                target_status=ShipmentStatus.READY,
            )
        )

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True
    assert uow.audit_logs.items == []


async def test_transition_shipment_status_enforces_tenant_isolation() -> None:
    uow = FakeUnitOfWork()

    shipment = make_shipment(
        tenant_id=uuid4(),
        status=ShipmentStatus.DRAFT,
    )

    uow.shipments.add(shipment)

    with pytest.raises(ShipmentNotFoundError):
        await TransitionShipmentStatus(uow).execute(
            TransitionShipmentStatusCommand(
                tenant_id=uuid4(),
                actor_id=uuid4(),
                shipment_id=shipment.id,
                target_status=ShipmentStatus.READY,
            )
        )

    assert shipment.status == ShipmentStatus.DRAFT
    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True
    assert uow.audit_logs.items == []
