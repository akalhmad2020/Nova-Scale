from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.shipments.domain.enums import (
    ServiceType,
    ShipmentStatus,
    WeightUnit,
)


class CreateShipmentRequest(BaseModel):
    customer_id: UUID
    origin_location_id: UUID
    destination_location_id: UUID

    tracking_number: str = Field(
        min_length=1,
        max_length=100,
    )
    reference: str | None = Field(
        default=None,
        max_length=150,
    )

    service_type: ServiceType

    description: str | None = Field(
        default=None,
        max_length=500,
    )

    weight: Decimal = Field(
        gt=0,
    )
    weight_unit: WeightUnit

    notes: str | None = None


class UpdateShipmentRequest(BaseModel):
    customer_id: UUID
    origin_location_id: UUID
    destination_location_id: UUID

    tracking_number: str = Field(
        min_length=1,
        max_length=100,
    )
    reference: str | None = Field(
        default=None,
        max_length=150,
    )

    service_type: ServiceType

    description: str | None = Field(
        default=None,
        max_length=500,
    )

    weight: Decimal = Field(
        gt=0,
    )
    weight_unit: WeightUnit

    notes: str | None = None


class TransitionShipmentStatusRequest(BaseModel):
    status: ShipmentStatus


class ShipmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    customer_id: UUID
    origin_location_id: UUID
    destination_location_id: UUID

    tracking_number: str
    reference: str | None

    status: ShipmentStatus
    service_type: ServiceType

    description: str | None

    weight: Decimal
    weight_unit: WeightUnit

    notes: str | None

    created_at: datetime
    updated_at: datetime
