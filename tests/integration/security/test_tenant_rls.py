from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.customers.infrastructure.models.customer import Customer
from app.modules.identity.infrastructure.models.tenant import Tenant

pytestmark = pytest.mark.integration


TENANT_SCOPED_TABLES = {
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
}


async def test_tenant_scoped_tables_have_rls_enabled_and_forced(
    db_session: AsyncSession,
) -> None:
    result = await db_session.execute(
        text(
            """
            SELECT
                c.relname AS table_name,
                c.relrowsecurity AS rls_enabled,
                c.relforcerowsecurity AS rls_forced
            FROM pg_class AS c
            JOIN pg_namespace AS n
                ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relkind = 'r'
              AND c.relname = ANY(:table_names)
            ORDER BY c.relname
            """
        ),
        {
            "table_names": list(TENANT_SCOPED_TABLES),
        },
    )

    rows = result.all()

    actual_tables = {row.table_name for row in rows}

    assert actual_tables == TENANT_SCOPED_TABLES

    for row in rows:
        assert row.rls_enabled is True, f"RLS is not enabled on table {row.table_name!r}"
        assert row.rls_forced is True, f"RLS is not forced on table {row.table_name!r}"


async def test_tenant_scoped_tables_have_tenant_isolation_policy(
    db_session: AsyncSession,
) -> None:
    result = await db_session.execute(
        text(
            """
            SELECT
                tablename
            FROM pg_policies
            WHERE schemaname = 'public'
              AND policyname = 'tenant_isolation'
              AND tablename = ANY(:table_names)
            """
        ),
        {
            "table_names": list(TENANT_SCOPED_TABLES),
        },
    )

    tables_with_policy = set(result.scalars().all())

    assert tables_with_policy == TENANT_SCOPED_TABLES


async def test_no_tenant_context_hides_tenant_scoped_rows(
    db_session: AsyncSession,
) -> None:
    await db_session.execute(
        text(
            """
            SELECT set_config(
                'app.current_tenant_id',
                '',
                true
            )
            """
        )
    )

    for table_name in (
        "customers",
        "shipments",
        "documents",
    ):
        result = await db_session.execute(text(f"SELECT count(*) FROM {table_name}"))

        assert result.scalar_one() == 0, (
            f"Table {table_name!r} exposed tenant rows without a tenant context."
        )


async def test_customer_rows_are_isolated_between_tenants(
    db_session: AsyncSession,
) -> None:
    tenant_a = Tenant(
        id=uuid4(),
        name="RLS Tenant A",
        slug=f"rls-tenant-a-{uuid4()}",
    )
    tenant_b = Tenant(
        id=uuid4(),
        name="RLS Tenant B",
        slug=f"rls-tenant-b-{uuid4()}",
    )

    db_session.add_all(
        [
            tenant_a,
            tenant_b,
        ]
    )
    await db_session.flush()

    await db_session.execute(
        text(
            """
            SELECT set_config(
                'app.current_tenant_id',
                :tenant_id,
                true
            )
            """
        ),
        {
            "tenant_id": str(tenant_a.id),
        },
    )

    customer_a = Customer(
        id=uuid4(),
        tenant_id=tenant_a.id,
        name="Customer A",
        code=f"CUSTOMER-A-{uuid4()}",
        email="customer-a@example.com",
    )

    db_session.add(customer_a)
    await db_session.flush()

    await db_session.execute(
        text(
            """
            SELECT set_config(
                'app.current_tenant_id',
                :tenant_id,
                true
            )
            """
        ),
        {
            "tenant_id": str(tenant_b.id),
        },
    )

    customer_b = Customer(
        id=uuid4(),
        tenant_id=tenant_b.id,
        name="Customer B",
        code=f"CUSTOMER-B-{uuid4()}",
        email="customer-b@example.com",
    )

    db_session.add(customer_b)
    await db_session.flush()

    await db_session.execute(
        text(
            """
            SELECT set_config(
                'app.current_tenant_id',
                :tenant_id,
                true
            )
            """
        ),
        {
            "tenant_id": str(tenant_a.id),
        },
    )

    tenant_a_result = await db_session.execute(
        select(Customer)
        .where(
            Customer.id.in_(
                [
                    customer_a.id,
                    customer_b.id,
                ]
            )
        )
        .order_by(Customer.id)
    )

    tenant_a_customers = tenant_a_result.scalars().all()

    assert [customer.id for customer in tenant_a_customers] == [
        customer_a.id,
    ]

    await db_session.execute(
        text(
            """
            SELECT set_config(
                'app.current_tenant_id',
                :tenant_id,
                true
            )
            """
        ),
        {
            "tenant_id": str(tenant_b.id),
        },
    )

    tenant_b_result = await db_session.execute(
        select(Customer)
        .where(
            Customer.id.in_(
                [
                    customer_a.id,
                    customer_b.id,
                ]
            )
        )
        .order_by(Customer.id)
    )

    tenant_b_customers = tenant_b_result.scalars().all()

    assert [customer.id for customer in tenant_b_customers] == [
        customer_b.id,
    ]

    await db_session.execute(
        text(
            """
            SELECT set_config(
                'app.current_tenant_id',
                '',
                true
            )
            """
        )
    )

    no_tenant_result = await db_session.execute(
        select(Customer).where(
            Customer.id.in_(
                [
                    customer_a.id,
                    customer_b.id,
                ]
            )
        )
    )

    assert no_tenant_result.scalars().all() == []


async def test_customer_insert_is_rejected_for_different_tenant_context(
    db_session: AsyncSession,
) -> None:
    tenant_a = Tenant(
        id=uuid4(),
        name="RLS Write Tenant A",
        slug=f"rls-write-tenant-a-{uuid4()}",
    )
    tenant_b = Tenant(
        id=uuid4(),
        name="RLS Write Tenant B",
        slug=f"rls-write-tenant-b-{uuid4()}",
    )

    db_session.add_all(
        [
            tenant_a,
            tenant_b,
        ]
    )
    await db_session.flush()

    await db_session.execute(
        text(
            """
            SELECT set_config(
                'app.current_tenant_id',
                :tenant_id,
                true
            )
            """
        ),
        {
            "tenant_id": str(tenant_a.id),
        },
    )

    cross_tenant_customer = Customer(
        id=uuid4(),
        tenant_id=tenant_b.id,
        name="Cross Tenant Customer",
        code=f"CROSS-TENANT-{uuid4()}",
        email="cross-tenant@example.com",
    )

    db_session.add(cross_tenant_customer)

    with pytest.raises(DBAPIError):
        await db_session.flush()

    await db_session.rollback()


async def test_customer_tenant_id_update_is_rejected(
    db_session: AsyncSession,
) -> None:
    tenant_a = Tenant(
        id=uuid4(),
        name="RLS Update Tenant A",
        slug=f"rls-update-tenant-a-{uuid4()}",
    )
    tenant_b = Tenant(
        id=uuid4(),
        name="RLS Update Tenant B",
        slug=f"rls-update-tenant-b-{uuid4()}",
    )

    db_session.add_all(
        [
            tenant_a,
            tenant_b,
        ]
    )
    await db_session.flush()

    await db_session.execute(
        text(
            """
            SELECT set_config(
                'app.current_tenant_id',
                :tenant_id,
                true
            )
            """
        ),
        {
            "tenant_id": str(tenant_a.id),
        },
    )

    customer = Customer(
        id=uuid4(),
        tenant_id=tenant_a.id,
        name="Tenant A Customer",
        code=f"TENANT-A-{uuid4()}",
        email="tenant-a-customer@example.com",
    )

    db_session.add(customer)
    await db_session.flush()

    customer.tenant_id = tenant_b.id

    with pytest.raises(DBAPIError):
        await db_session.flush()

    await db_session.rollback()
