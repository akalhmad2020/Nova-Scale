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

from app.modules.documents.domain.enums import LabelStatus
from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ShipmentLabel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shipment_labels"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="shipment_label_tenant_id",
        ),
        ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="shipment_label_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "shipment_id"],
            ["shipments.tenant_id", "shipments.id"],
            name="shipment_label_shipment",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "package_id"],
            ["packages.tenant_id", "packages.id"],
            name="shipment_label_package",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "carrier_id"],
            ["carriers.tenant_id", "carriers.id"],
            name="shipment_label_carrier",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "carrier_service_id"],
            ["carrier_services.tenant_id", "carrier_services.id"],
            name="shipment_label_carrier_service",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "document_id"],
            ["documents.tenant_id", "documents.id"],
            name="shipment_label_document",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('pending', 'generated', 'voided', 'failed')",
            name="shipment_label_status_valid",
        ),
        CheckConstraint(
            "tracking_number IS NULL OR length(btrim(tracking_number)) > 0",
            name="shipment_label_tracking_nonblank",
        ),
        Index(
            "ix_shipment_labels_tenant_shipment",
            "tenant_id",
            "shipment_id",
        ),
        Index(
            "ix_shipment_labels_tenant_package",
            "tenant_id",
            "package_id",
        ),
        Index(
            "ix_shipment_labels_tenant_status",
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

    package_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )

    carrier_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )

    carrier_service_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )

    status: Mapped[LabelStatus] = mapped_column(
        String(20),
        nullable=False,
        default=LabelStatus.PENDING,
    )

    tracking_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    document_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
