from uuid import uuid4

import pytest

from app.modules.customers.application.exceptions import (
    CustomerCodeAlreadyExistsError,
    CustomerNotFoundError,
)
from app.modules.customers.application.use_cases.update_customer import (
    UpdateCustomer,
    UpdateCustomerCommand,
)
from app.modules.customers.domain.enums import CustomerStatus
from app.modules.customers.infrastructure.models.customer import Customer
from tests.unit.customers.fakes import FakeUnitOfWork


async def test_update_customer_updates_fields() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    customer = Customer(
        tenant_id=tenant_id,
        name="Old Name",
        code="OLD-001",
        email="old@example.com",
        phone="123",
        notes="Old notes",
        status=CustomerStatus.ACTIVE,
    )
    customer.id = uuid4()

    uow.customers.add(customer)

    use_case = UpdateCustomer(uow)

    result = await use_case.execute(
        UpdateCustomerCommand(
            tenant_id=tenant_id,
            customer_id=customer.id,
            name="  New Name  ",
            code="  new-001  ",
            email="  NEW@EXAMPLE.COM  ",
            phone="  456  ",
            notes="  New notes  ",
        )
    )

    assert result is customer
    assert customer.name == "New Name"
    assert customer.code == "NEW-001"
    assert customer.email == "new@example.com"
    assert customer.phone == "456"
    assert customer.notes == "New notes"

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.rolled_back is False


async def test_update_customer_rejects_unknown_customer() -> None:
    uow = FakeUnitOfWork()

    use_case = UpdateCustomer(uow)

    with pytest.raises(CustomerNotFoundError):
        await use_case.execute(
            UpdateCustomerCommand(
                tenant_id=uuid4(),
                customer_id=uuid4(),
                name="Customer",
                code="CUST-001",
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_update_customer_rejects_customer_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    customer = Customer(
        tenant_id=uuid4(),
        name="Customer",
        code="CUST-001",
        status=CustomerStatus.ACTIVE,
    )
    customer.id = uuid4()

    uow.customers.add(customer)

    use_case = UpdateCustomer(uow)

    with pytest.raises(CustomerNotFoundError):
        await use_case.execute(
            UpdateCustomerCommand(
                tenant_id=uuid4(),
                customer_id=customer.id,
                name="Updated",
                code="UPDATED-001",
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_update_customer_rejects_duplicate_code() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    first = Customer(
        tenant_id=tenant_id,
        name="First",
        code="CUST-001",
        status=CustomerStatus.ACTIVE,
    )

    second = Customer(
        tenant_id=tenant_id,
        name="Second",
        code="CUST-002",
        status=CustomerStatus.ACTIVE,
    )

    first.id = uuid4()
    second.id = uuid4()

    uow.customers.add(first)
    uow.customers.add(second)

    use_case = UpdateCustomer(uow)

    with pytest.raises(CustomerCodeAlreadyExistsError):
        await use_case.execute(
            UpdateCustomerCommand(
                tenant_id=tenant_id,
                customer_id=second.id,
                name="Second Updated",
                code=" cust-001 ",
            )
        )

    assert second.code == "CUST-002"
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_update_customer_allows_same_existing_code() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    customer = Customer(
        tenant_id=tenant_id,
        name="Customer",
        code="CUST-001",
        status=CustomerStatus.ACTIVE,
    )
    customer.id = uuid4()

    uow.customers.add(customer)

    use_case = UpdateCustomer(uow)

    result = await use_case.execute(
        UpdateCustomerCommand(
            tenant_id=tenant_id,
            customer_id=customer.id,
            name="Updated Customer",
            code="cust-001",
        )
    )

    assert result is customer
    assert result.code == "CUST-001"
    assert result.name == "Updated Customer"

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.rolled_back is False
