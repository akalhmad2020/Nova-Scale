from datetime import UTC, datetime
from uuid import uuid4

from app.modules.customers.application.use_cases.list_customers import (
    ListCustomers,
    ListCustomersQuery,
)
from app.modules.customers.domain.enums import CustomerStatus
from app.modules.customers.infrastructure.models.customer import Customer
from tests.unit.customers.fakes import FakeUnitOfWork


async def test_list_customers_returns_customers_for_tenant() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    first = Customer(
        tenant_id=tenant_id,
        name="First Customer",
        code="CUST-001",
        status=CustomerStatus.ACTIVE,
    )

    second = Customer(
        tenant_id=tenant_id,
        name="Second Customer",
        code="CUST-002",
        status=CustomerStatus.ACTIVE,
    )

    uow.customers.add(first)
    uow.customers.add(second)

    use_case = ListCustomers(uow)

    result = await use_case.execute(
        ListCustomersQuery(
            tenant_id=tenant_id,
        )
    )

    assert result == [first, second]


async def test_list_customers_excludes_other_tenants() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()
    other_tenant_id = uuid4()

    expected = Customer(
        tenant_id=tenant_id,
        name="Expected Customer",
        code="CUST-001",
        status=CustomerStatus.ACTIVE,
    )

    other = Customer(
        tenant_id=other_tenant_id,
        name="Other Customer",
        code="CUST-002",
        status=CustomerStatus.ACTIVE,
    )

    uow.customers.add(expected)
    uow.customers.add(other)

    use_case = ListCustomers(uow)

    result = await use_case.execute(
        ListCustomersQuery(
            tenant_id=tenant_id,
        )
    )

    assert result == [expected]


async def test_list_customers_excludes_soft_deleted_customers() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    active = Customer(
        tenant_id=tenant_id,
        name="Active Customer",
        code="CUST-001",
        status=CustomerStatus.ACTIVE,
    )

    deleted = Customer(
        tenant_id=tenant_id,
        name="Deleted Customer",
        code="CUST-002",
        status=CustomerStatus.ACTIVE,
    )
    deleted.deleted_at = datetime.now(UTC)

    uow.customers.add(active)
    uow.customers.add(deleted)

    use_case = ListCustomers(uow)

    result = await use_case.execute(
        ListCustomersQuery(
            tenant_id=tenant_id,
        )
    )

    assert result == [active]


async def test_list_customers_returns_empty_list() -> None:
    uow = FakeUnitOfWork()

    use_case = ListCustomers(uow)

    result = await use_case.execute(
        ListCustomersQuery(
            tenant_id=uuid4(),
        )
    )

    assert result == []
