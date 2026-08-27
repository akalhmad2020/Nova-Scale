from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.modules.rates.domain.enums import RateQuoteStatus


class CreateRateQuoteRequest(BaseModel):
    currency: str = Field(
        min_length=3,
        max_length=3,
    )

    base_amount: Decimal = Field(
        ge=0,
    )

    surcharge_amount: Decimal = Field(
        ge=0,
    )

    expires_at: datetime | None = None

    @field_validator(
        "currency",
        mode="before",
    )
    @classmethod
    def normalize_currency(
        cls,
        value: object,
    ) -> object:
        if isinstance(value, str):
            return value.strip().upper()

        return value


class TransitionRateQuoteStatusRequest(BaseModel):
    status: RateQuoteStatus


class RateQuoteResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    tenant_id: UUID
    shipment_id: UUID

    currency: str

    base_amount: Decimal
    surcharge_amount: Decimal
    total_amount: Decimal

    status: RateQuoteStatus
    expires_at: datetime | None

    created_at: datetime
    updated_at: datetime
