from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.locations.domain.enums import (
    LocationStatus,
    LocationType,
)


class CreateLocationRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=200,
    )
    code: str = Field(
        min_length=1,
        max_length=100,
    )
    type: LocationType

    country_code: str = Field(
        min_length=2,
        max_length=2,
    )
    state: str | None = Field(
        default=None,
        max_length=150,
    )
    city: str = Field(
        min_length=1,
        max_length=150,
    )
    postal_code: str | None = Field(
        default=None,
        max_length=32,
    )
    address_line1: str = Field(
        min_length=1,
        max_length=300,
    )
    address_line2: str | None = Field(
        default=None,
        max_length=300,
    )

    contact_name: str | None = Field(
        default=None,
        max_length=200,
    )
    email: EmailStr | None = None
    phone: str | None = Field(
        default=None,
        max_length=50,
    )

    latitude: Decimal | None = Field(
        default=None,
        ge=Decimal("-90"),
        le=Decimal("90"),
    )
    longitude: Decimal | None = Field(
        default=None,
        ge=Decimal("-180"),
        le=Decimal("180"),
    )

    notes: str | None = None


class UpdateLocationRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=200,
    )
    code: str = Field(
        min_length=1,
        max_length=100,
    )
    type: LocationType

    country_code: str = Field(
        min_length=2,
        max_length=2,
    )
    state: str | None = Field(
        default=None,
        max_length=150,
    )
    city: str = Field(
        min_length=1,
        max_length=150,
    )
    postal_code: str | None = Field(
        default=None,
        max_length=32,
    )
    address_line1: str = Field(
        min_length=1,
        max_length=300,
    )
    address_line2: str | None = Field(
        default=None,
        max_length=300,
    )

    contact_name: str | None = Field(
        default=None,
        max_length=200,
    )
    email: EmailStr | None = None
    phone: str | None = Field(
        default=None,
        max_length=50,
    )

    latitude: Decimal | None = Field(
        default=None,
        ge=Decimal("-90"),
        le=Decimal("90"),
    )
    longitude: Decimal | None = Field(
        default=None,
        ge=Decimal("-180"),
        le=Decimal("180"),
    )

    notes: str | None = None


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID

    name: str
    code: str
    type: LocationType

    contact_name: str | None
    email: str | None
    phone: str | None

    country_code: str
    state: str | None
    city: str
    postal_code: str | None
    address_line1: str
    address_line2: str | None

    latitude: Decimal | None
    longitude: Decimal | None

    status: LocationStatus
    notes: str | None

    created_at: datetime
    updated_at: datetime
