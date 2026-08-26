from app.modules.shipments.domain.enums import ShipmentStatus

ALLOWED_SHIPMENT_STATUS_TRANSITIONS: dict[
    ShipmentStatus,
    frozenset[ShipmentStatus],
] = {
    ShipmentStatus.DRAFT: frozenset(
        {
            ShipmentStatus.READY,
            ShipmentStatus.CANCELLED,
        }
    ),
    ShipmentStatus.READY: frozenset(
        {
            ShipmentStatus.IN_TRANSIT,
            ShipmentStatus.CANCELLED,
        }
    ),
    ShipmentStatus.IN_TRANSIT: frozenset(
        {
            ShipmentStatus.DELIVERED,
        }
    ),
    ShipmentStatus.DELIVERED: frozenset(),
    ShipmentStatus.CANCELLED: frozenset(),
}


def can_transition_shipment_status(
    current_status: ShipmentStatus,
    target_status: ShipmentStatus,
) -> bool:
    return target_status in ALLOWED_SHIPMENT_STATUS_TRANSITIONS[current_status]
