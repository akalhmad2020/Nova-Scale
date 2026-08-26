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
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.locations.domain.enums import (
    LocationStatus,
    LocationType,
)
from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Location(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "locations"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "code",
        ),
        Index(
            "ix_locations_tenant_id",
            "tenant_id",
        ),
        Index(
            "ix_locations_country_code",
            "country_code",
        ),
        Index(
            "ix_locations_city",
            "city",
        ),
        CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name="latitude_range",
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="longitude_range",
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

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    type: Mapped[LocationType] = mapped_column(
        SQLEnum(
            LocationType,
            name="location_type",
            native_enum=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=LocationType.OTHER,
        server_default=LocationType.OTHER.value,
    )

    contact_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    country_code: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )

    state: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    city: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    postal_code: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    address_line1: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    address_line2: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )

    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=9,
            scale=6,
        ),
        nullable=True,
    )

    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=9,
            scale=6,
        ),
        nullable=True,
    )

    status: Mapped[LocationStatus] = mapped_column(
        SQLEnum(
            LocationStatus,
            name="location_status",
            native_enum=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=LocationStatus.ACTIVE,
        server_default=LocationStatus.ACTIVE.value,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
