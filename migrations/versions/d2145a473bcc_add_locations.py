"""add locations

Revision ID: d2145a473bcc
Revises: b26daa05cfbe
Create Date: 2026-08-26 17:55:00.286034
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d2145a473bcc"
down_revision: str | Sequence[str] | None = "b26daa05cfbe"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


location_type = postgresql.ENUM(
    "warehouse",
    "office",
    "store",
    "pickup",
    "delivery",
    "other",
    name="location_type",
    create_type=False,
)

location_status = postgresql.ENUM(
    "active",
    "inactive",
    name="location_status",
    create_type=False,
)


def upgrade() -> None:
    location_type.create(
        op.get_bind(),
        checkfirst=True,
    )

    location_status.create(
        op.get_bind(),
        checkfirst=True,
    )

    op.create_table(
        "locations",
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
            "type",
            location_type,
            server_default="other",
            nullable=False,
        ),
        sa.Column(
            "contact_name",
            sa.String(length=200),
            nullable=True,
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
            "country_code",
            sa.String(length=2),
            nullable=False,
        ),
        sa.Column(
            "state",
            sa.String(length=150),
            nullable=True,
        ),
        sa.Column(
            "city",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "postal_code",
            sa.String(length=32),
            nullable=True,
        ),
        sa.Column(
            "address_line1",
            sa.String(length=300),
            nullable=False,
        ),
        sa.Column(
            "address_line2",
            sa.String(length=300),
            nullable=True,
        ),
        sa.Column(
            "latitude",
            sa.Numeric(
                precision=9,
                scale=6,
            ),
            nullable=True,
        ),
        sa.Column(
            "longitude",
            sa.Numeric(
                precision=9,
                scale=6,
            ),
            nullable=True,
        ),
        sa.Column(
            "status",
            location_status,
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
        sa.CheckConstraint(
            "latitude IS NULL OR "
            "(latitude >= -90 AND latitude <= 90)",
            name=op.f("ck_locations_latitude_range"),
        ),
        sa.CheckConstraint(
            "longitude IS NULL OR "
            "(longitude >= -180 AND longitude <= 180)",
            name=op.f("ck_locations_longitude_range"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_locations_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_locations"),
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "code",
            name=op.f("uq_locations_tenant_id_code"),
        ),
    )

    op.create_index(
        "ix_locations_city",
        "locations",
        ["city"],
        unique=False,
    )

    op.create_index(
        "ix_locations_country_code",
        "locations",
        ["country_code"],
        unique=False,
    )

    op.create_index(
        "ix_locations_tenant_id",
        "locations",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_locations_tenant_id",
        table_name="locations",
    )

    op.drop_index(
        "ix_locations_country_code",
        table_name="locations",
    )

    op.drop_index(
        "ix_locations_city",
        table_name="locations",
    )

    op.drop_table("locations")

    location_status.drop(
        op.get_bind(),
        checkfirst=True,
    )

    location_type.drop(
        op.get_bind(),
        checkfirst=True,
    )