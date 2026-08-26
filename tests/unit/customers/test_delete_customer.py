from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.customers.application.exceptions import CustomerNotFoundError
from app.modules.customers.application.use_cases.delete_customer import (
    DeleteCustomer,
    DeleteCustomerCommand,
)
from app.modules.customers.domain.enums import CustomerStatus
from app.modules.customers.infrastructure.models.customer import Customer
from tests.unit.customers.fakes import FakeUnitOfWork


async def test_delete_customer_soft_deletes_customer() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    customer = Customer(
        tenant_id=tenant_id,
        name="Acme Trading",
        code="ACME-001",
        status=CustomerStatus.ACTIVE,
    )
    customer.id = uuid4()

    uow.customers.add(customer)

    use_case = DeleteCustomer(uow)

    await use_case.execute(
        DeleteCustomerCommand(
            tenant_id=tenant_id,
            customer_id=customer.id,
        )
    )

    assert customer.deleted_at is not None

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.rolled_back is False


async def test_delete_customer_rejects_unknown_customer() -> None:
    uow = FakeUnitOfWork()

    use_case = DeleteCustomer(uow)

    with pytest.raises(CustomerNotFoundError):
        await use_case.execute(
            DeleteCustomerCommand(
                tenant_id=uuid4(),
                customer_id=uuid4(),
            )
        )

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_delete_customer_rejects_customer_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    customer = Customer(
        tenant_id=uuid4(),
        name="Other Tenant Customer",
        code="OTHER-001",
        status=CustomerStatus.ACTIVE,
    )
    customer.id = uuid4()

    uow.customers.add(customer)

    use_case = DeleteCustomer(uow)

    with pytest.raises(CustomerNotFoundError):
        await use_case.execute(
            DeleteCustomerCommand(
                tenant_id=uuid4(),
                customer_id=customer.id,
            )
        )

    assert customer.deleted_at is None

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_delete_customer_rejects_already_deleted_customer() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    customer = Customer(
        tenant_id=tenant_id,
        name="Deleted Customer",
        code="DELETED-001",
        status=CustomerStatus.ACTIVE,
    )
    customer.id = uuid4()
    customer.deleted_at = datetime.now(UTC)

    uow.customers.add(customer)

    use_case = DeleteCustomer(uow)

    with pytest.raises(CustomerNotFoundError):
        await use_case.execute(
            DeleteCustomerCommand(
                tenant_id=tenant_id,
                customer_id=customer.id,
            )
        )

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True
