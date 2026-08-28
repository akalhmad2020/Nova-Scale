"""create documents and shipment labels

Revision ID: beec6fa472a1
Revises: 1b3ad6336232
Create Date: 2026-08-28 15:48:15.561893
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "beec6fa472a1"
down_revision: str | Sequence[str] | None = "1b3ad6336232"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Parent composite keys must exist before child foreign keys reference them.
    op.create_unique_constraint(
        "shipment_tenant_id",
        "shipments",
        ["tenant_id", "id"],
    )
    op.create_unique_constraint(
        "package_tenant_id",
        "packages",
        ["tenant_id", "id"],
    )
    op.create_unique_constraint(
        "carrier_service_tenant_id",
        "carrier_services",
        ["tenant_id", "id"],
    )

    op.create_table(
        "documents",
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
            "type",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "filename",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "content_type",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "storage_key",
            sa.String(length=500),
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
            "status IN ('pending', 'ready', 'failed')",
            name=op.f("ck_documents_document_status_valid"),
        ),
        sa.CheckConstraint(
            "type IN ('shipping_label', 'commercial_invoice', 'packing_slip', 'other')",
            name=op.f("ck_documents_document_type_valid"),
        ),
        sa.CheckConstraint(
            "length(btrim(content_type)) > 0",
            name=op.f("ck_documents_document_content_type_nonblank"),
        ),
        sa.CheckConstraint(
            "length(btrim(filename)) > 0",
            name=op.f("ck_documents_document_filename_nonblank"),
        ),
        sa.CheckConstraint(
            "length(btrim(storage_key)) > 0",
            name=op.f("ck_documents_document_storage_key_nonblank"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "shipment_id"],
            ["shipments.tenant_id", "shipments.id"],
            name="document_shipment",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="document_tenant",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_documents"),
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "id",
            name="document_tenant_id",
        ),
    )

    op.create_index(
        "ix_documents_tenant_shipment",
        "documents",
        ["tenant_id", "shipment_id"],
        unique=False,
    )
    op.create_index(
        "ix_documents_tenant_status",
        "documents",
        ["tenant_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_documents_tenant_type",
        "documents",
        ["tenant_id", "type"],
        unique=False,
    )

    op.create_table(
        "shipment_labels",
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
            "package_id",
            sa.UUID(),
            nullable=True,
        ),
        sa.Column(
            "carrier_id",
            sa.UUID(),
            nullable=True,
        ),
        sa.Column(
            "carrier_service_id",
            sa.UUID(),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "tracking_number",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "document_id",
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
        sa.CheckConstraint(
            "status IN ('pending', 'generated', 'voided', 'failed')",
            name=op.f("ck_shipment_labels_shipment_label_status_valid"),
        ),
        sa.CheckConstraint(
            "tracking_number IS NULL OR length(btrim(tracking_number)) > 0",
            name=op.f("ck_shipment_labels_shipment_label_tracking_nonblank"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "carrier_id"],
            ["carriers.tenant_id", "carriers.id"],
            name="shipment_label_carrier",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "carrier_service_id"],
            ["carrier_services.tenant_id", "carrier_services.id"],
            name="shipment_label_carrier_service",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "document_id"],
            ["documents.tenant_id", "documents.id"],
            name="shipment_label_document",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "package_id"],
            ["packages.tenant_id", "packages.id"],
            name="shipment_label_package",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "shipment_id"],
            ["shipments.tenant_id", "shipments.id"],
            name="shipment_label_shipment",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="shipment_label_tenant",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_shipment_labels"),
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "id",
            name="shipment_label_tenant_id",
        ),
    )

    op.create_index(
        "ix_shipment_labels_tenant_package",
        "shipment_labels",
        ["tenant_id", "package_id"],
        unique=False,
    )
    op.create_index(
        "ix_shipment_labels_tenant_shipment",
        "shipment_labels",
        ["tenant_id", "shipment_id"],
        unique=False,
    )
    op.create_index(
        "ix_shipment_labels_tenant_status",
        "shipment_labels",
        ["tenant_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    # Child tables must be removed before the parent composite keys.
    op.drop_index(
        "ix_shipment_labels_tenant_status",
        table_name="shipment_labels",
    )
    op.drop_index(
        "ix_shipment_labels_tenant_shipment",
        table_name="shipment_labels",
    )
    op.drop_index(
        "ix_shipment_labels_tenant_package",
        table_name="shipment_labels",
    )
    op.drop_table("shipment_labels")

    op.drop_index(
        "ix_documents_tenant_type",
        table_name="documents",
    )
    op.drop_index(
        "ix_documents_tenant_status",
        table_name="documents",
    )
    op.drop_index(
        "ix_documents_tenant_shipment",
        table_name="documents",
    )
    op.drop_table("documents")

    op.drop_constraint(
        "carrier_service_tenant_id",
        "carrier_services",
        type_="unique",
    )
    op.drop_constraint(
        "package_tenant_id",
        "packages",
        type_="unique",
    )
    op.drop_constraint(
        "shipment_tenant_id",
        "shipments",
        type_="unique",
    )
