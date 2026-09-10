from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.ai.application.action_exceptions import AgentActionProposalRejectedError
from app.ai.application.services.prepare_shipment_action import (
    PrepareShipmentActionService,
)
from app.modules.shipments.application.use_cases.get_shipment import GetShipment
from app.modules.shipments.domain.enums import ShipmentStatus
from app.modules.shipments.domain.lifecycle import can_transition_shipment_status
from app.modules.shipments.infrastructure.models.shipment import Shipment


def make_get_shipment(
    *,
    status: ShipmentStatus,
    notes: str | None = "Original notes",
) -> GetShipment:
    shipment = cast(
        Shipment,
        SimpleNamespace(
            id=uuid4(),
            tracking_number="SHIP-001",
            status=status,
            notes=notes,
        ),
    )

    service = MagicMock(spec=GetShipment)
    service.execute = AsyncMock(return_value=shipment)

    return cast(GetShipment, service)


def find_valid_transition() -> tuple[ShipmentStatus, ShipmentStatus]:
    for current in ShipmentStatus:
        for target in ShipmentStatus:
            if current != target and can_transition_shipment_status(current, target):
                return current, target

    raise AssertionError("Shipment lifecycle must contain at least one valid transition")


@pytest.mark.asyncio
async def test_prepare_transition_returns_structured_proposal() -> None:
    tenant_id = uuid4()
    current, target = find_valid_transition()
    get_shipment = make_get_shipment(status=current)
    service = PrepareShipmentActionService(get_shipment=get_shipment)

    proposal = await service.prepare_transition(
        tenant_id=tenant_id,
        shipment_id=uuid4(),
        shipment_identifier="SHIP-001",
        target_status=target,
    )

    assert proposal.action_type == "transition_shipment_status"
    assert proposal.expected_status == current
    assert proposal.target_status == target
    assert proposal.shipment_identifier == "SHIP-001"
    assert "requires explicit confirmation" in proposal.confirmation_message


@pytest.mark.asyncio
async def test_prepare_transition_rejects_noop() -> None:
    status = next(iter(ShipmentStatus))
    service = PrepareShipmentActionService(
        get_shipment=make_get_shipment(status=status),
    )

    with pytest.raises(AgentActionProposalRejectedError):
        await service.prepare_transition(
            tenant_id=uuid4(),
            shipment_id=uuid4(),
            shipment_identifier="SHIP-001",
            target_status=status,
        )


@pytest.mark.asyncio
async def test_prepare_notes_update_preserves_requested_notes() -> None:
    status = next(iter(ShipmentStatus))
    service = PrepareShipmentActionService(
        get_shipment=make_get_shipment(status=status),
    )

    proposal = await service.prepare_notes_update(
        tenant_id=uuid4(),
        shipment_id=uuid4(),
        shipment_identifier="SHIP-001",
        new_notes="  Keep   upright  ",
    )

    assert proposal.action_type == "update_shipment_notes"
    assert proposal.expected_notes == "Original notes"
    assert proposal.new_notes == "Keep upright"


@pytest.mark.asyncio
async def test_prepare_notes_update_rejects_existing_value() -> None:
    status = next(iter(ShipmentStatus))
    service = PrepareShipmentActionService(
        get_shipment=make_get_shipment(
            status=status,
            notes="Keep upright",
        ),
    )

    with pytest.raises(AgentActionProposalRejectedError):
        await service.prepare_notes_update(
            tenant_id=uuid4(),
            shipment_id=uuid4(),
            shipment_identifier="SHIP-001",
            new_notes="Keep upright",
        )
