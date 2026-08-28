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

from app.modules.carriers.domain.enums import CarrierServiceStatus
from app.modules.shipments.domain.enums import ServiceType
from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class CarrierService(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "carrier_services"

    __table_args__ = (
        ForeignKeyConstraint(
            [
                "tenant_id",
                "carrier_id",
            ],
            [
                "carriers.tenant_id",
                "carriers.id",
            ],
            ondelete="RESTRICT",
            name="carrier_service_carrier",
        ),
        UniqueConstraint(
            "tenant_id",
            "carrier_id",
            "code",
            name="carrier_service_code",
        ),
        CheckConstraint(
            "char_length(trim(code)) > 0",
            name="code_not_blank",
        ),
        CheckConstraint(
            "char_length(trim(name)) > 0",
            name="name_not_blank",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive')",
            name="status_valid",
        ),
        Index(
            "ix_carrier_services_tenant_carrier_status",
            "tenant_id",
            "carrier_id",
            "status",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )

    carrier_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )

    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    service_type: Mapped[ServiceType] = mapped_column(
        String(20),
        nullable=False,
    )

    status: Mapped[CarrierServiceStatus] = mapped_column(
        String(20),
        nullable=False,
        default=CarrierServiceStatus.ACTIVE,
    )
