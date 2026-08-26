from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.customers.domain.enums import CustomerStatus


class CreateCustomerRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=200,
    )
    code: str = Field(
        min_length=1,
        max_length=100,
    )
    email: EmailStr | None = None
    phone: str | None = Field(
        default=None,
        max_length=50,
    )
    notes: str | None = None


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    code: str
    email: str | None
    phone: str | None
    status: CustomerStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class UpdateCustomerRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=200,
    )
    code: str = Field(
        min_length=1,
        max_length=100,
    )
    email: EmailStr | None = None
    phone: str | None = Field(
        default=None,
        max_length=50,
    )
    notes: str | None = None
