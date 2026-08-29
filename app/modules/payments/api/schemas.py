from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.payments.domain.enums import PaymentMethod, PaymentStatus


class CreatePaymentRequest(BaseModel):
    customer_id: UUID

    payment_number: str = Field(
        min_length=1,
        max_length=50,
    )

    currency: str = Field(
        min_length=3,
        max_length=3,
    )

    amount: Decimal = Field(
        gt=Decimal("0"),
        max_digits=18,
        decimal_places=2,
    )

    method: PaymentMethod

    reference: str | None = Field(
        default=None,
        max_length=255,
    )

    received_at: datetime | None = None

    @field_validator(
        "payment_number",
        "currency",
        mode="before",
    )
    @classmethod
    def validate_nonblank_string(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("must not be blank")

        return value

    @field_validator(
        "reference",
        mode="before",
    )
    @classmethod
    def validate_reference(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None

        return value


class AddPaymentAllocationRequest(BaseModel):
    invoice_id: UUID

    amount: Decimal = Field(
        gt=Decimal("0"),
        max_digits=18,
        decimal_places=2,
    )


class PaymentAllocationResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    tenant_id: UUID
    payment_id: UUID
    invoice_id: UUID

    amount: Decimal

    created_at: datetime
    updated_at: datetime


class PaymentResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    tenant_id: UUID
    customer_id: UUID

    payment_number: str
    status: PaymentStatus
    currency: str
    amount: Decimal
    method: PaymentMethod

    reference: str | None
    received_at: datetime | None
    posted_at: datetime | None

    created_at: datetime
    updated_at: datetime
