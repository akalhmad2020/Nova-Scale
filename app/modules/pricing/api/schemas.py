from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.pricing.domain.enums import PricingRuleStatus
from app.modules.shipments.domain.enums import ServiceType


class CreatePricingRuleRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=200,
    )

    service_type: ServiceType

    currency: str = Field(
        min_length=3,
        max_length=3,
    )

    base_amount: Decimal = Field(
        ge=0,
    )

    price_per_kg: Decimal = Field(
        ge=0,
    )

    surcharge_amount: Decimal = Field(
        ge=0,
    )

    valid_from: datetime | None = None
    valid_until: datetime | None = None


class PricingRuleResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    tenant_id: UUID

    name: str
    service_type: ServiceType
    currency: str

    base_amount: Decimal
    price_per_kg: Decimal
    surcharge_amount: Decimal

    status: PricingRuleStatus

    valid_from: datetime | None
    valid_until: datetime | None

    created_at: datetime
    updated_at: datetime


class UpdatePricingRuleRequest(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    service_type: ServiceType | None = None

    currency: str | None = Field(
        default=None,
        min_length=3,
        max_length=3,
    )

    base_amount: Decimal | None = Field(
        default=None,
        ge=0,
    )

    price_per_kg: Decimal | None = Field(
        default=None,
        ge=0,
    )

    surcharge_amount: Decimal | None = Field(
        default=None,
        ge=0,
    )

    valid_from: datetime | None = None
    valid_until: datetime | None = None
