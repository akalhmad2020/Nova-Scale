"""add packages

Revision ID: b04fb2c2bc04
Revises: 33e2a504f6fd
Create Date: 2026-08-27 14:09:18.393417
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b04fb2c2bc04"
down_revision: str | Sequence[str] | None = "33e2a504f6fd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "packages",
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
            "package_number",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "weight",
            sa.Numeric(precision=12, scale=3),
            nullable=False,
        ),
        sa.Column(
            "weight_unit",
            sa.String(length=10),
            nullable=False,
        ),
        sa.Column(
            "length",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
        ),
        sa.Column(
            "width",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
        ),
        sa.Column(
            "height",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
        ),
        sa.Column(
            "dimension_unit",
            sa.String(length=10),
            nullable=True,
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
        sa.CheckConstraint(
            "weight > 0",
            name=op.f("ck_packages_weight_positive"),
        ),
        sa.CheckConstraint(
            "length IS NULL OR length > 0",
            name=op.f("ck_packages_length_positive"),
        ),
        sa.CheckConstraint(
            "width IS NULL OR width > 0",
            name=op.f("ck_packages_width_positive"),
        ),
        sa.CheckConstraint(
            "height IS NULL OR height > 0",
            name=op.f("ck_packages_height_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"],
            ["shipments.id"],
            name=op.f("fk_packages_shipment_id_shipments"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_packages_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_packages"),
        ),
        sa.UniqueConstraint(
            "shipment_id",
            "package_number",
            name=op.f(
                "uq_packages_shipment_id_package_number"
            ),
        ),
    )

    op.create_index(
        "ix_packages_shipment_id",
        "packages",
        ["shipment_id"],
        unique=False,
    )

    op.create_index(
        "ix_packages_tenant_id",
        "packages",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_packages_tenant_id",
        table_name="packages",
    )

    op.drop_index(
        "ix_packages_shipment_id",
        table_name="packages",
    )

    op.drop_table("packages")