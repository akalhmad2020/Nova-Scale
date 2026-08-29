"""create payments foundation

Revision ID: 0ba10e0f9618
Revises: 50a934f25ca1
Create Date: 2026-08-28 22:37:53.034964
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0ba10e0f9618"

down_revision: str | Sequence[str] | None = "50a934f25ca1"

branch_labels: str | Sequence[str] | None = None

depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column(
            "tenant_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "payment_number",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=False,
        ),
        sa.Column(
            "amount",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
        ),
        sa.Column(
            "method",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "reference",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "posted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("uuidv7()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'posted', 'void')",
            name=op.f("ck_payments_status_valid"),
        ),
        sa.CheckConstraint(
            "method IN ('bank_transfer', 'cash', 'card', 'check', 'other')",
            name=op.f("ck_payments_method_valid"),
        ),
        sa.CheckConstraint(
            "amount > 0",
            name=op.f("ck_payments_amount_positive"),
        ),
        sa.CheckConstraint(
            "length(currency) = 3",
            name=op.f("ck_payments_currency_length"),
        ),
        sa.CheckConstraint(
            "length(trim(payment_number)) > 0",
            name=op.f("ck_payments_payment_number_nonblank"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "customer_id"],
            ["customers.tenant_id", "customers.id"],
            name=op.f("fk_payments_tenant_id_customer_id_customers"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_payments_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_payments"),
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "id",
            name="payment_tenant_id",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "payment_number",
            name="payment_tenant_payment_number",
        ),
    )

    op.create_index(
        "ix_payments_tenant_customer",
        "payments",
        ["tenant_id", "customer_id"],
        unique=False,
    )

    op.create_index(
        "ix_payments_tenant_received_at",
        "payments",
        ["tenant_id", "received_at"],
        unique=False,
    )

    op.create_index(
        "ix_payments_tenant_status",
        "payments",
        ["tenant_id", "status"],
        unique=False,
    )

    op.create_table(
        "payment_allocations",
        sa.Column(
            "tenant_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "payment_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "invoice_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "amount",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
        ),
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("uuidv7()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "amount > 0",
            name=op.f("ck_payment_allocations_amount_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "invoice_id"],
            ["invoices.tenant_id", "invoices.id"],
            name=op.f("fk_payment_allocations_tenant_id_invoice_id_invoices"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "payment_id"],
            ["payments.tenant_id", "payments.id"],
            name=op.f("fk_payment_allocations_tenant_id_payment_id_payments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_payment_allocations_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_payment_allocations"),
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "id",
            name="payment_allocation_tenant_id",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "payment_id",
            "invoice_id",
            name="payment_allocation_payment_invoice",
        ),
    )

    op.create_index(
        "ix_payment_allocations_tenant_invoice",
        "payment_allocations",
        ["tenant_id", "invoice_id"],
        unique=False,
    )

    op.create_index(
        "ix_payment_allocations_tenant_payment",
        "payment_allocations",
        ["tenant_id", "payment_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_payment_allocations_tenant_payment",
        table_name="payment_allocations",
    )

    op.drop_index(
        "ix_payment_allocations_tenant_invoice",
        table_name="payment_allocations",
    )

    op.drop_table("payment_allocations")

    op.drop_index(
        "ix_payments_tenant_status",
        table_name="payments",
    )

    op.drop_index(
        "ix_payments_tenant_received_at",
        table_name="payments",
    )

    op.drop_index(
        "ix_payments_tenant_customer",
        table_name="payments",
    )

    op.drop_table("payments")
