import pytest

from app.modules.shipments.domain.enums import ShipmentStatus
from app.modules.shipments.domain.lifecycle import (
    can_transition_shipment_status,
)


@pytest.mark.parametrize(
    ("current_status", "target_status"),
    [
        (
            ShipmentStatus.DRAFT,
            ShipmentStatus.READY,
        ),
        (
            ShipmentStatus.DRAFT,
            ShipmentStatus.CANCELLED,
        ),
        (
            ShipmentStatus.READY,
            ShipmentStatus.IN_TRANSIT,
        ),
        (
            ShipmentStatus.READY,
            ShipmentStatus.CANCELLED,
        ),
        (
            ShipmentStatus.IN_TRANSIT,
            ShipmentStatus.DELIVERED,
        ),
    ],
)
def test_allows_valid_shipment_status_transitions(
    current_status: ShipmentStatus,
    target_status: ShipmentStatus,
) -> None:
    assert can_transition_shipment_status(
        current_status,
        target_status,
    )


@pytest.mark.parametrize(
    ("current_status", "target_status"),
    [
        (
            ShipmentStatus.DRAFT,
            ShipmentStatus.DELIVERED,
        ),
        (
            ShipmentStatus.DRAFT,
            ShipmentStatus.IN_TRANSIT,
        ),
        (
            ShipmentStatus.READY,
            ShipmentStatus.DELIVERED,
        ),
        (
            ShipmentStatus.IN_TRANSIT,
            ShipmentStatus.READY,
        ),
        (
            ShipmentStatus.IN_TRANSIT,
            ShipmentStatus.CANCELLED,
        ),
        (
            ShipmentStatus.DELIVERED,
            ShipmentStatus.DRAFT,
        ),
        (
            ShipmentStatus.DELIVERED,
            ShipmentStatus.CANCELLED,
        ),
        (
            ShipmentStatus.CANCELLED,
            ShipmentStatus.DRAFT,
        ),
        (
            ShipmentStatus.CANCELLED,
            ShipmentStatus.IN_TRANSIT,
        ),
    ],
)
def test_rejects_invalid_shipment_status_transitions(
    current_status: ShipmentStatus,
    target_status: ShipmentStatus,
) -> None:
    assert not can_transition_shipment_status(
        current_status,
        target_status,
    )
