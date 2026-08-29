from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.payments.domain.enums import PaymentStatus
from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    __table_args__ = (
        CheckConstraint(
            "method IN ('bank_transfer', 'cash', 'card', 'check', 'other')",
            name="method_valid",
        ),
        UniqueConstraint(
            "tenant_id",
            "id",
            name="payment_tenant_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "payment_number",
            name="payment_tenant_payment_number",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "customer_id"],
            ["customers.tenant_id", "customers.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('draft', 'posted', 'void')",
            name="status_valid",
        ),
        CheckConstraint(
            "amount > 0",
            name="amount_positive",
        ),
        CheckConstraint(
            "length(trim(payment_number)) > 0",
            name="payment_number_nonblank",
        ),
        CheckConstraint(
            "length(currency) = 3",
            name="currency_length",
        ),
        Index(
            "ix_payments_tenant_customer",
            "tenant_id",
            "customer_id",
        ),
        Index(
            "ix_payments_tenant_status",
            "tenant_id",
            "status",
        ),
        Index(
            "ix_payments_tenant_received_at",
            "tenant_id",
            "received_at",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )

    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )

    payment_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PaymentStatus.DRAFT,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    method: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
