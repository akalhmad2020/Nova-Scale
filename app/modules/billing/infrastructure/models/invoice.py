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

from app.modules.billing.domain.enums import InvoiceStatus
from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Invoice(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "invoices"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="invoice_tenant_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "invoice_number",
            name="invoice_tenant_invoice_number",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "customer_id"],
            ["customers.tenant_id", "customers.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('draft', 'issued', 'paid', 'void')",
            name="status",
        ),
        CheckConstraint(
            "subtotal >= 0",
            name="subtotal_non_negative",
        ),
        CheckConstraint(
            "tax_amount >= 0",
            name="tax_amount_non_negative",
        ),
        CheckConstraint(
            "total_amount >= 0",
            name="total_amount_non_negative",
        ),
        CheckConstraint(
            "total_amount = subtotal + tax_amount",
            name="total_matches_components",
        ),
        Index(
            "ix_invoices_tenant_customer",
            "tenant_id",
            "customer_id",
        ),
        Index(
            "ix_invoices_tenant_status",
            "tenant_id",
            "status",
        ),
        Index(
            "ix_invoices_tenant_due_at",
            "tenant_id",
            "due_at",
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
        nullable=False,
    )

    invoice_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=InvoiceStatus.DRAFT,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    issued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
