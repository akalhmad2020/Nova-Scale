"""add rate quotes

Revision ID: 7bf98504fcfd
Revises: 0c6dd3d848e0
Create Date: 2026-08-27 19:48:40.102409
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "7bf98504fcfd"
down_revision: str | Sequence[str] | None = "0c6dd3d848e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rate_quotes",
        sa.Column(
            "tenant_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "shipment_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=False,
        ),
        sa.Column(
            "base_amount",
            sa.Numeric(
                precision=14,
                scale=2,
            ),
            nullable=False,
        ),
        sa.Column(
            "surcharge_amount",
            sa.Numeric(
                precision=14,
                scale=2,
            ),
            nullable=False,
        ),
        sa.Column(
            "total_amount",
            sa.Numeric(
                precision=14,
                scale=2,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
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
            "base_amount >= 0",
            name=op.f(
                "ck_rate_quotes_base_amount_non_negative"
            ),
        ),
        sa.CheckConstraint(
            "surcharge_amount >= 0",
            name=op.f(
                "ck_rate_quotes_surcharge_amount_non_negative"
            ),
        ),
        sa.CheckConstraint(
            "total_amount >= 0",
            name=op.f(
                "ck_rate_quotes_total_amount_non_negative"
            ),
        ),
        sa.CheckConstraint(
            "total_amount = base_amount + surcharge_amount",
            name=op.f(
                "ck_rate_quotes_total_amount_consistent"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"],
            ["shipments.id"],
            name=op.f(
                "fk_rate_quotes_shipment_id_shipments"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f(
                "fk_rate_quotes_tenant_id_tenants"
            ),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_rate_quotes"),
        ),
    )

    op.create_index(
        "ix_rate_quotes_shipment_id",
        "rate_quotes",
        ["shipment_id"],
        unique=False,
    )

    op.create_index(
        "ix_rate_quotes_status",
        "rate_quotes",
        ["status"],
        unique=False,
    )

    op.create_index(
        "ix_rate_quotes_tenant_id",
        "rate_quotes",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rate_quotes_tenant_id",
        table_name="rate_quotes",
    )

    op.drop_index(
        "ix_rate_quotes_status",
        table_name="rate_quotes",
    )

    op.drop_index(
        "ix_rate_quotes_shipment_id",
        table_name="rate_quotes",
    )

    op.drop_table("rate_quotes")