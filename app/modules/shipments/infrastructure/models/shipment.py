from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy import (
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.shipments.domain.enums import (
    ServiceType,
    ShipmentStatus,
    WeightUnit,
)
from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Shipment(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "shipments"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "tracking_number",
        ),
        Index(
            "ix_shipments_tenant_id",
            "tenant_id",
        ),
        Index(
            "ix_shipments_customer_id",
            "customer_id",
        ),
        Index(
            "ix_shipments_origin_location_id",
            "origin_location_id",
        ),
        Index(
            "ix_shipments_destination_location_id",
            "destination_location_id",
        ),
        Index(
            "ix_shipments_status",
            "status",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "tenants.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "customers.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    origin_location_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "locations.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    destination_location_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "locations.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    tracking_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    reference: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    status: Mapped[ShipmentStatus] = mapped_column(
        SQLEnum(
            ShipmentStatus,
            name="shipment_status",
            native_enum=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=ShipmentStatus.DRAFT,
        server_default=ShipmentStatus.DRAFT.value,
    )

    service_type: Mapped[ServiceType] = mapped_column(
        SQLEnum(
            ServiceType,
            name="shipment_service_type",
            native_enum=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=ServiceType.STANDARD,
        server_default=ServiceType.STANDARD.value,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    weight: Mapped[Decimal] = mapped_column(
        Numeric(
            precision=12,
            scale=3,
        ),
        nullable=False,
    )

    weight_unit: Mapped[WeightUnit] = mapped_column(
        SQLEnum(
            WeightUnit,
            name="shipment_weight_unit",
            native_enum=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=WeightUnit.KG,
        server_default=WeightUnit.KG.value,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
