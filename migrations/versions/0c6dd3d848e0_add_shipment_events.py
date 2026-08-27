"""add shipment events

Revision ID: 0c6dd3d848e0
Revises: b04fb2c2bc04
Create Date: 2026-08-27 15:17:15.595356
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0c6dd3d848e0"
down_revision: str | Sequence[str] | None = "b04fb2c2bc04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shipment_events",
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
            "event_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "location_id",
            sa.UUID(),
            nullable=True,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(
                astext_type=sa.Text(),
            ),
            nullable=True,
        ),
        sa.Column(
            "created_by_user_id",
            sa.UUID(),
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
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f(
                "fk_shipment_events_created_by_user_id_users"
            ),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            name=op.f(
                "fk_shipment_events_location_id_locations"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"],
            ["shipments.id"],
            name=op.f(
                "fk_shipment_events_shipment_id_shipments"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f(
                "fk_shipment_events_tenant_id_tenants"
            ),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_shipment_events"),
        ),
    )

    op.create_index(
        "ix_shipment_events_occurred_at",
        "shipment_events",
        ["occurred_at"],
        unique=False,
    )

    op.create_index(
        "ix_shipment_events_shipment_id",
        "shipment_events",
        ["shipment_id"],
        unique=False,
    )

    op.create_index(
        "ix_shipment_events_shipment_occurred_at",
        "shipment_events",
        [
            "shipment_id",
            "occurred_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_shipment_events_tenant_id",
        "shipment_events",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_shipment_events_tenant_id",
        table_name="shipment_events",
    )

    op.drop_index(
        "ix_shipment_events_shipment_occurred_at",
        table_name="shipment_events",
    )

    op.drop_index(
        "ix_shipment_events_shipment_id",
        table_name="shipment_events",
    )

    op.drop_index(
        "ix_shipment_events_occurred_at",
        table_name="shipment_events",
    )

    op.drop_table("shipment_events")