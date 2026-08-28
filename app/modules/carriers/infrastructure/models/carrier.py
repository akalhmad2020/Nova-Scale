from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.carriers.domain.enums import CarrierStatus
from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Carrier(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "carriers"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="carrier_tenant_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "code",
            name="carrier_tenant_code",
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
            "ix_carriers_tenant_status",
            "tenant_id",
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

    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    status: Mapped[CarrierStatus] = mapped_column(
        String(20),
        nullable=False,
        default=CarrierStatus.ACTIVE,
    )
