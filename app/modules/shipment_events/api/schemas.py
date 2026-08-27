from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.shipment_events.domain.enums import ShipmentEventType
from app.modules.shipments.domain.enums import ShipmentStatus


class RecordShipmentEventRequest(BaseModel):
    event_type: ShipmentEventType
    occurred_at: datetime
    status: ShipmentStatus | None = None
    location_id: UUID | None = None
    description: str | None = Field(
        default=None,
        max_length=2000,
    )
    metadata: dict[str, object] | None = None


class ShipmentEventResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: UUID
    tenant_id: UUID
    shipment_id: UUID

    event_type: ShipmentEventType
    status: ShipmentStatus | None

    location_id: UUID | None
    description: str | None
    occurred_at: datetime

    metadata: dict[str, object] | None = Field(
        validation_alias="metadata_",
        serialization_alias="metadata",
    )

    created_by_user_id: UUID | None

    created_at: datetime
    updated_at: datetime
