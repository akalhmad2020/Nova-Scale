from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.packages.domain.enums import DimensionUnit
from app.modules.shipments.domain.enums import WeightUnit
from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Package(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "packages"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="package_tenant_id",
        ),
        UniqueConstraint(
            "shipment_id",
            "package_number",
        ),
        CheckConstraint(
            "weight > 0",
            name="weight_positive",
        ),
        CheckConstraint(
            "length IS NULL OR length > 0",
            name="length_positive",
        ),
        CheckConstraint(
            "width IS NULL OR width > 0",
            name="width_positive",
        ),
        CheckConstraint(
            "height IS NULL OR height > 0",
            name="height_positive",
        ),
        Index(
            "ix_packages_tenant_id",
            "tenant_id",
        ),
        Index(
            "ix_packages_shipment_id",
            "shipment_id",
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

    shipment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "shipments.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    package_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
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
        String(10),
        nullable=False,
    )

    length: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=10,
            scale=2,
        ),
        nullable=True,
    )

    width: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=10,
            scale=2,
        ),
        nullable=True,
    )

    height: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=10,
            scale=2,
        ),
        nullable=True,
    )

    dimension_unit: Mapped[DimensionUnit | None] = mapped_column(
        String(10),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
