from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.documents.domain.enums import (
    DocumentStatus,
    DocumentType,
    LabelStatus,
)


class CreateDocumentRequest(BaseModel):
    document_type: DocumentType

    filename: str = Field(
        min_length=1,
        max_length=255,
    )

    content_type: str = Field(
        min_length=1,
        max_length=100,
    )

    storage_key: str = Field(
        min_length=1,
        max_length=500,
    )

    @field_validator(
        "filename",
        "content_type",
        "storage_key",
        mode="before",
    )
    @classmethod
    def validate_nonblank_string(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("must not be blank")

        return value


class DocumentResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    tenant_id: UUID
    shipment_id: UUID

    type: DocumentType
    status: DocumentStatus

    filename: str
    content_type: str
    storage_key: str

    created_at: datetime
    updated_at: datetime


class CreateShipmentLabelRequest(BaseModel):
    package_id: UUID | None = None
    carrier_id: UUID | None = None
    carrier_service_id: UUID | None = None


class CompleteShipmentLabelRequest(BaseModel):
    document_id: UUID

    tracking_number: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    @field_validator(
        "tracking_number",
        mode="before",
    )
    @classmethod
    def validate_tracking_number(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("must not be blank")

        return value


class ShipmentLabelResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    tenant_id: UUID
    shipment_id: UUID

    package_id: UUID | None
    carrier_id: UUID | None
    carrier_service_id: UUID | None

    status: LabelStatus
    tracking_number: str | None
    document_id: UUID | None

    created_at: datetime
    updated_at: datetime
