from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.pricing.domain.enums import PricingRuleStatus
from app.modules.shipments.domain.enums import ServiceType
from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class PricingRule(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "pricing_rules"

    __table_args__ = (
        CheckConstraint(
            "base_amount >= 0",
            name="base_amount_non_negative",
        ),
        CheckConstraint(
            "price_per_kg >= 0",
            name="price_per_kg_non_negative",
        ),
        CheckConstraint(
            "surcharge_amount >= 0",
            name="surcharge_amount_non_negative",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_from IS NULL OR valid_until > valid_from",
            name="validity_range_valid",
        ),
        Index(
            "ix_pricing_rules_tenant_id",
            "tenant_id",
        ),
        Index(
            "ix_pricing_rules_service_type",
            "service_type",
        ),
        Index(
            "ix_pricing_rules_status",
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

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    service_type: Mapped[ServiceType] = mapped_column(
        String(20),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    base_amount: Mapped[Decimal] = mapped_column(
        Numeric(
            precision=14,
            scale=2,
        ),
        nullable=False,
    )

    price_per_kg: Mapped[Decimal] = mapped_column(
        Numeric(
            precision=14,
            scale=4,
        ),
        nullable=False,
    )

    surcharge_amount: Mapped[Decimal] = mapped_column(
        Numeric(
            precision=14,
            scale=2,
        ),
        nullable=False,
    )

    status: Mapped[PricingRuleStatus] = mapped_column(
        String(20),
        nullable=False,
        default=PricingRuleStatus.ACTIVE,
    )

    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
