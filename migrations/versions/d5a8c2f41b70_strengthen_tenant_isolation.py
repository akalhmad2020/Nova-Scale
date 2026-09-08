"""strengthen tenant isolation

Revision ID: d5a8c2f41b70
Revises: c4f2a1b7e903
Create Date: 2026-09-07 22:55:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5a8c2f41b70"
down_revision: str | Sequence[str] | None = "c4f2a1b7e903"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Data-plane tables are protected by PostgreSQL RLS in addition to application
# scoping. Control-plane/bootstrap and globally-polled queue tables are deliberately
# excluded; those are still tenant-scoped in repositories and documented separately.
RLS_TABLES = (
    "audit_logs",
    "carrier_services",
    "carriers",
    "customers",
    "documents",
    "invoice_lines",
    "invoices",
    "journal_entries",
    "journal_lines",
    "locations",
    "packages",
    "payment_allocations",
    "payments",
    "pricing_rules",
    "rag_chunks",
    "rate_quotes",
    "shipment_events",
    "shipment_labels",
    "shipments",
)


RLS_PREDICATE = (
    "tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid"
)


def upgrade() -> None:
    # Composite references make cross-tenant associations invalid at the database
    # boundary, even if a future application bug accidentally supplies mixed ids.
    op.create_unique_constraint(
        "location_tenant_id",
        "locations",
        ["tenant_id", "id"],
    )

    op.drop_constraint(
        "fk_shipments_customer_id_customers",
        "shipments",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_shipments_origin_location_id_locations",
        "shipments",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_shipments_destination_location_id_locations",
        "shipments",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_shipments_tenant_customer",
        "shipments",
        "customers",
        ["tenant_id", "customer_id"],
        ["tenant_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_shipments_tenant_origin_location",
        "shipments",
        "locations",
        ["tenant_id", "origin_location_id"],
        ["tenant_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_shipments_tenant_destination_location",
        "shipments",
        "locations",
        ["tenant_id", "destination_location_id"],
        ["tenant_id", "id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "fk_packages_shipment_id_shipments",
        "packages",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_packages_tenant_shipment",
        "packages",
        "shipments",
        ["tenant_id", "shipment_id"],
        ["tenant_id", "id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "fk_shipment_events_shipment_id_shipments",
        "shipment_events",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_shipment_events_location_id_locations",
        "shipment_events",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_shipment_events_tenant_shipment",
        "shipment_events",
        "shipments",
        ["tenant_id", "shipment_id"],
        ["tenant_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_shipment_events_tenant_location",
        "shipment_events",
        "locations",
        ["tenant_id", "location_id"],
        ["tenant_id", "id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "fk_rate_quotes_shipment_id_shipments",
        "rate_quotes",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_rate_quotes_tenant_shipment",
        "rate_quotes",
        "shipments",
        ["tenant_id", "shipment_id"],
        ["tenant_id", "id"],
        ondelete="RESTRICT",
    )

    for table_name in RLS_TABLES:
        op.execute(sa.text(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY'))
        op.execute(sa.text(f'ALTER TABLE "{table_name}" FORCE ROW LEVEL SECURITY'))
        op.execute(
            sa.text(
                f'''CREATE POLICY tenant_isolation ON "{table_name}"
                    FOR ALL
                    USING ({RLS_PREDICATE})
                    WITH CHECK ({RLS_PREDICATE})'''
            )
        )


def downgrade() -> None:
    for table_name in reversed(RLS_TABLES):
        op.execute(sa.text(f'DROP POLICY IF EXISTS tenant_isolation ON "{table_name}"'))
        op.execute(sa.text(f'ALTER TABLE "{table_name}" NO FORCE ROW LEVEL SECURITY'))
        op.execute(sa.text(f'ALTER TABLE "{table_name}" DISABLE ROW LEVEL SECURITY'))

    op.drop_constraint(
        "fk_rate_quotes_tenant_shipment",
        "rate_quotes",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_rate_quotes_shipment_id_shipments",
        "rate_quotes",
        "shipments",
        ["shipment_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "fk_shipment_events_tenant_location",
        "shipment_events",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_shipment_events_tenant_shipment",
        "shipment_events",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_shipment_events_shipment_id_shipments",
        "shipment_events",
        "shipments",
        ["shipment_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_shipment_events_location_id_locations",
        "shipment_events",
        "locations",
        ["location_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "fk_packages_tenant_shipment",
        "packages",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_packages_shipment_id_shipments",
        "packages",
        "shipments",
        ["shipment_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "fk_shipments_tenant_destination_location",
        "shipments",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_shipments_tenant_origin_location",
        "shipments",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_shipments_tenant_customer",
        "shipments",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_shipments_customer_id_customers",
        "shipments",
        "customers",
        ["customer_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_shipments_origin_location_id_locations",
        "shipments",
        "locations",
        ["origin_location_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_shipments_destination_location_id_locations",
        "shipments",
        "locations",
        ["destination_location_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "location_tenant_id",
        "locations",
        type_="unique",
    )
