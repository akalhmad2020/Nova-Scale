from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.billing.domain.enums import InvoiceStatus


class CreateInvoiceRequest(BaseModel):
    customer_id: UUID

    invoice_number: str = Field(
        min_length=1,
        max_length=50,
    )

    currency: str = Field(
        min_length=3,
        max_length=3,
    )

    tax_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    @field_validator(
        "invoice_number",
        "currency",
        mode="before",
    )
    @classmethod
    def validate_nonblank_string(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("must not be blank")

        return value


class AddInvoiceLineRequest(BaseModel):
    shipment_id: UUID | None = None

    description: str = Field(
        min_length=1,
        max_length=500,
    )

    quantity: Decimal = Field(
        gt=Decimal("0"),
        max_digits=18,
        decimal_places=4,
    )

    unit_price: Decimal = Field(
        ge=Decimal("0"),
        max_digits=18,
        decimal_places=2,
    )

    @field_validator(
        "description",
        mode="before",
    )
    @classmethod
    def validate_description(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("must not be blank")

        return value


class InvoiceLineResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    tenant_id: UUID
    invoice_id: UUID
    shipment_id: UUID | None

    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal

    created_at: datetime
    updated_at: datetime


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    tenant_id: UUID
    customer_id: UUID

    invoice_number: str
    status: InvoiceStatus
    currency: str

    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal

    issued_at: datetime | None
    due_at: datetime | None
    paid_at: datetime | None

    created_at: datetime
    updated_at: datetime
