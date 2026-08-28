from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.documents.domain.enums import DocumentStatus, DocumentType
from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="document_tenant_id",
        ),
        ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="document_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "shipment_id"],
            ["shipments.tenant_id", "shipments.id"],
            name="document_shipment",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "length(btrim(filename)) > 0",
            name="document_filename_nonblank",
        ),
        CheckConstraint(
            "length(btrim(content_type)) > 0",
            name="document_content_type_nonblank",
        ),
        CheckConstraint(
            "length(btrim(storage_key)) > 0",
            name="document_storage_key_nonblank",
        ),
        CheckConstraint(
            "type IN ('shipping_label', 'commercial_invoice', 'packing_slip', 'other')",
            name="document_type_valid",
        ),
        CheckConstraint(
            "status IN ('pending', 'ready', 'failed')",
            name="document_status_valid",
        ),
        Index(
            "ix_documents_tenant_shipment",
            "tenant_id",
            "shipment_id",
        ),
        Index(
            "ix_documents_tenant_type",
            "tenant_id",
            "type",
        ),
        Index(
            "ix_documents_tenant_status",
            "tenant_id",
            "status",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )

    shipment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )

    type: Mapped[DocumentType] = mapped_column(
        String(30),
        nullable=False,
    )

    status: Mapped[DocumentStatus] = mapped_column(
        String(20),
        nullable=False,
        default=DocumentStatus.PENDING,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    storage_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
