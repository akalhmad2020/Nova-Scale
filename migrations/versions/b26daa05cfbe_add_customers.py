"""add customers

Revision ID: b26daa05cfbe
Revises: 7e9e43b37ba0
Create Date: 2026-08-26 13:13:44.126545
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b26daa05cfbe"
down_revision: str | Sequence[str] | None = "7e9e43b37ba0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


customer_status = postgresql.ENUM(
    "active",
    "inactive",
    name="customer_status",
    create_type=False,
)


def upgrade() -> None:
    customer_status.create(
        op.get_bind(),
        checkfirst=True,
    )

    op.create_table(
        "customers",
        sa.Column(
            "tenant_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "code",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "email",
            sa.String(length=320),
            nullable=True,
        ),
        sa.Column(
            "phone",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "status",
            customer_status,
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "notes",
            sa.Text(),
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
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_customers_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_customers"),
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "code",
            name=op.f("uq_customers_tenant_id_code"),
        ),
    )

    op.create_index(
        "ix_customers_email",
        "customers",
        ["email"],
        unique=False,
    )

    op.create_index(
        "ix_customers_tenant_id",
        "customers",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_customers_tenant_id",
        table_name="customers",
    )

    op.drop_index(
        "ix_customers_email",
        table_name="customers",
    )

    op.drop_table("customers")

    customer_status.drop(
        op.get_bind(),
        checkfirst=True,
    )
