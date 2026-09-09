from enum import Enum
from uuid import UUID

from app.ai.application.agent.shipment_summary_models import (
    ShipmentEventSummary,
    ShipmentSummaryContext,
)
from app.modules.shipment_events.application.use_cases.list_shipment_events import (
    ListShipmentEvents,
    ListShipmentEventsQuery,
)
from app.modules.shipments.application.use_cases.get_shipment import (
    GetShipment,
    GetShipmentQuery,
)


def enum_value(value: object) -> str:
    if isinstance(value, Enum):
        return str(value.value)

    return str(value)


class ShipmentSummaryTool:
    def __init__(
        self,
        *,
        get_shipment: GetShipment,
        list_shipment_events: ListShipmentEvents,
    ) -> None:
        self._get_shipment = get_shipment
        self._list_shipment_events = list_shipment_events

    async def execute(
        self,
        *,
        tenant_id: UUID,
        shipment_id: UUID,
    ) -> ShipmentSummaryContext:
        shipment = await self._get_shipment.execute(
            GetShipmentQuery(
                tenant_id=tenant_id,
                shipment_id=shipment_id,
            )
        )

        shipment_events = await self._list_shipment_events.execute(
            ListShipmentEventsQuery(
                tenant_id=tenant_id,
                shipment_id=shipment_id,
            )
        )

        ordered_events = sorted(
            shipment_events,
            key=lambda event: event.occurred_at,
        )

        events = tuple(
            ShipmentEventSummary(
                id=event.id,
                event_type=enum_value(event.event_type),
                status=(enum_value(event.status) if event.status is not None else None),
                location_id=event.location_id,
                description=event.description,
                occurred_at=event.occurred_at,
                metadata=event.metadata_,
            )
            for event in ordered_events
        )

        latest_event = events[-1] if events else None

        return ShipmentSummaryContext(
            shipment_id=shipment.id,
            tenant_id=shipment.tenant_id,
            tracking_number=shipment.tracking_number,
            reference=shipment.reference,
            status=enum_value(shipment.status),
            service_type=enum_value(shipment.service_type),
            description=shipment.description,
            weight=shipment.weight,
            weight_unit=enum_value(shipment.weight_unit),
            notes=shipment.notes,
            customer_id=shipment.customer_id,
            origin_location_id=shipment.origin_location_id,
            destination_location_id=shipment.destination_location_id,
            event_count=len(events),
            latest_event=latest_event,
            events=events,
        )
