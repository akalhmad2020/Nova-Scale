from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ShipmentEventSummary:
    id: UUID
    event_type: str
    status: str | None
    location_id: UUID | None
    description: str | None
    occurred_at: datetime
    metadata: dict[str, object] | None


@dataclass(frozen=True, slots=True)
class ShipmentSummaryContext:
    shipment_id: UUID
    tenant_id: UUID
    tracking_number: str
    reference: str | None
    status: str
    service_type: str
    description: str | None
    weight: Decimal
    weight_unit: str
    notes: str | None
    customer_id: UUID
    origin_location_id: UUID
    destination_location_id: UUID
    event_count: int
    latest_event: ShipmentEventSummary | None
    events: tuple[ShipmentEventSummary, ...]
