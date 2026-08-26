"""add shipments

Revision ID: 33e2a504f6fd
Revises: d2145a473bcc
Create Date: 2026-08-26 19:18:17.434050
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "33e2a504f6fd"
down_revision: str | Sequence[str] | None = "d2145a473bcc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


shipment_status = postgresql.ENUM(
    "draft",
    "ready",
    "in_transit",
    "delivered",
    "cancelled",
    name="shipment_status",
    create_type=False,
)

shipment_service_type = postgresql.ENUM(
    "standard",
    "express",
    name="shipment_service_type",
    create_type=False,
)

shipment_weight_unit = postgresql.ENUM(
    "kg",
    "lb",
    name="shipment_weight_unit",
    create_type=False,
)


def upgrade() -> None:
    shipment_status.create(
        op.get_bind(),
        checkfirst=True,
    )

    shipment_service_type.create(
        op.get_bind(),
        checkfirst=True,
    )

    shipment_weight_unit.create(
        op.get_bind(),
        checkfirst=True,
    )

    op.create_table(
        "shipments",
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
            "origin_location_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "destination_location_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "tracking_number",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "reference",
            sa.String(length=150),
            nullable=True,
        ),
        sa.Column(
            "status",
            shipment_status,
            server_default="draft",
            nullable=False,
        ),
        sa.Column(
            "service_type",
            shipment_service_type,
            server_default="standard",
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "weight",
            sa.Numeric(
                precision=12,
                scale=3,
            ),
            nullable=False,
        ),
        sa.Column(
            "weight_unit",
            shipment_weight_unit,
            server_default="kg",
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
            ["customer_id"],
            ["customers.id"],
            name=op.f("fk_shipments_customer_id_customers"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["destination_location_id"],
            ["locations.id"],
            name=op.f(
                "fk_shipments_destination_location_id_locations"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["origin_location_id"],
            ["locations.id"],
            name=op.f(
                "fk_shipments_origin_location_id_locations"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_shipments_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_shipments"),
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "tracking_number",
            name=op.f(
                "uq_shipments_tenant_id_tracking_number"
            ),
        ),
    )

    op.create_index(
        "ix_shipments_customer_id",
        "shipments",
        ["customer_id"],
        unique=False,
    )

    op.create_index(
        "ix_shipments_destination_location_id",
        "shipments",
        ["destination_location_id"],
        unique=False,
    )

    op.create_index(
        "ix_shipments_origin_location_id",
        "shipments",
        ["origin_location_id"],
        unique=False,
    )

    op.create_index(
        "ix_shipments_status",
        "shipments",
        ["status"],
        unique=False,
    )

    op.create_index(
        "ix_shipments_tenant_id",
        "shipments",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_shipments_tenant_id",
        table_name="shipments",
    )

    op.drop_index(
        "ix_shipments_status",
        table_name="shipments",
    )

    op.drop_index(
        "ix_shipments_origin_location_id",
        table_name="shipments",
    )

    op.drop_index(
        "ix_shipments_destination_location_id",
        table_name="shipments",
    )

    op.drop_index(
        "ix_shipments_customer_id",
        table_name="shipments",
    )

    op.drop_table("shipments")

    shipment_weight_unit.drop(
        op.get_bind(),
        checkfirst=True,
    )

    shipment_service_type.drop(
        op.get_bind(),
        checkfirst=True,
    )

    shipment_status.drop(
        op.get_bind(),
        checkfirst=True,
    )