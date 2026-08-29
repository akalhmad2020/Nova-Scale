from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class PaymentAllocation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payment_allocations"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="payment_allocation_tenant_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "payment_id",
            "invoice_id",
            name="payment_allocation_payment_invoice",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "payment_id"],
            ["payments.tenant_id", "payments.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "invoice_id"],
            ["invoices.tenant_id", "invoices.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "amount > 0",
            name="amount_positive",
        ),
        Index(
            "ix_payment_allocations_tenant_payment",
            "tenant_id",
            "payment_id",
        ),
        Index(
            "ix_payment_allocations_tenant_invoice",
            "tenant_id",
            "invoice_id",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )

    payment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )

    invoice_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )
