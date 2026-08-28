from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.carriers.domain.enums import (
    CarrierServiceStatus,
    CarrierStatus,
)
from app.modules.shipments.domain.enums import ServiceType


class CreateCarrierRequest(BaseModel):
    code: str = Field(
        min_length=1,
        max_length=50,
    )

    name: str = Field(
        min_length=1,
        max_length=200,
    )


class CarrierResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    tenant_id: UUID

    code: str
    name: str
    status: CarrierStatus

    created_at: datetime
    updated_at: datetime


class UpdateCarrierRequest(BaseModel):
    code: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )


class CreateCarrierServiceRequest(BaseModel):
    code: str = Field(
        min_length=1,
        max_length=50,
    )

    name: str = Field(
        min_length=1,
        max_length=200,
    )

    service_type: ServiceType


class CarrierServiceResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    tenant_id: UUID
    carrier_id: UUID

    code: str
    name: str
    service_type: ServiceType
    status: CarrierServiceStatus

    created_at: datetime
    updated_at: datetime


class UpdateCarrierServiceRequest(BaseModel):
    code: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    service_type: ServiceType | None = None
