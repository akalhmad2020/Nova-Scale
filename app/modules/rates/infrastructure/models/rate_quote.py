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

from app.modules.rates.domain.enums import RateQuoteStatus
from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class RateQuote(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "rate_quotes"

    __table_args__ = (
        CheckConstraint(
            "base_amount >= 0",
            name="base_amount_non_negative",
        ),
        CheckConstraint(
            "surcharge_amount >= 0",
            name="surcharge_amount_non_negative",
        ),
        CheckConstraint(
            "total_amount >= 0",
            name="total_amount_non_negative",
        ),
        CheckConstraint(
            "total_amount = base_amount + surcharge_amount",
            name="total_amount_consistent",
        ),
        Index(
            "ix_rate_quotes_tenant_id",
            "tenant_id",
        ),
        Index(
            "ix_rate_quotes_shipment_id",
            "shipment_id",
        ),
        Index(
            "ix_rate_quotes_status",
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

    shipment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "shipments.id",
            ondelete="RESTRICT",
        ),
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

    surcharge_amount: Mapped[Decimal] = mapped_column(
        Numeric(
            precision=14,
            scale=2,
        ),
        nullable=False,
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(
            precision=14,
            scale=2,
        ),
        nullable=False,
    )

    status: Mapped[RateQuoteStatus] = mapped_column(
        String(20),
        nullable=False,
        default=RateQuoteStatus.DRAFT,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
