from uuid import uuid4

import pytest

from app.modules.customers.application.exceptions import (
    CustomerCodeAlreadyExistsError,
)
from app.modules.customers.application.use_cases.create_customer import (
    CreateCustomer,
    CreateCustomerCommand,
)
from app.modules.customers.domain.enums import CustomerStatus
from app.modules.customers.infrastructure.models.customer import Customer
from tests.unit.customers.fakes import FakeUnitOfWork


async def test_create_customer_creates_active_customer() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    use_case = CreateCustomer(uow)

    customer = await use_case.execute(
        CreateCustomerCommand(
            tenant_id=tenant_id,
            name="Acme Trading",
            code="ACME-001",
            email="contact@acme.example",
            phone="+970599000000",
            notes="Important customer",
        )
    )

    assert len(uow.customers.customers) == 1
    assert uow.customers.customers[0] is customer

    assert customer.tenant_id == tenant_id
    assert customer.name == "Acme Trading"
    assert customer.code == "ACME-001"
    assert customer.email == "contact@acme.example"
    assert customer.phone == "+970599000000"
    assert customer.notes == "Important customer"
    assert customer.status is CustomerStatus.ACTIVE

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.rolled_back is False


async def test_create_customer_normalizes_code() -> None:
    uow = FakeUnitOfWork()

    use_case = CreateCustomer(uow)

    customer = await use_case.execute(
        CreateCustomerCommand(
            tenant_id=uuid4(),
            name="Acme Trading",
            code="  acme-001  ",
        )
    )

    assert customer.code == "ACME-001"


async def test_create_customer_normalizes_email() -> None:
    uow = FakeUnitOfWork()

    use_case = CreateCustomer(uow)

    customer = await use_case.execute(
        CreateCustomerCommand(
            tenant_id=uuid4(),
            name="Acme Trading",
            code="ACME-001",
            email="  CONTACT@ACME.EXAMPLE  ",
        )
    )

    assert customer.email == "contact@acme.example"


async def test_create_customer_trims_fields() -> None:
    uow = FakeUnitOfWork()

    use_case = CreateCustomer(uow)

    customer = await use_case.execute(
        CreateCustomerCommand(
            tenant_id=uuid4(),
            name="  Acme Trading  ",
            code="ACME-001",
            phone="  +970599000000  ",
            notes="  Important customer  ",
        )
    )

    assert customer.name == "Acme Trading"
    assert customer.phone == "+970599000000"
    assert customer.notes == "Important customer"


async def test_create_customer_rejects_duplicate_code_in_same_tenant() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    existing = Customer(
        tenant_id=tenant_id,
        name="Existing Customer",
        code="ACME-001",
        status=CustomerStatus.ACTIVE,
    )

    uow.customers.add(existing)

    use_case = CreateCustomer(uow)

    with pytest.raises(CustomerCodeAlreadyExistsError):
        await use_case.execute(
            CreateCustomerCommand(
                tenant_id=tenant_id,
                name="Another Customer",
                code="acme-001",
            )
        )

    assert len(uow.customers.customers) == 1
    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_create_customer_allows_same_code_in_different_tenant() -> None:
    uow = FakeUnitOfWork()

    first_tenant_id = uuid4()
    second_tenant_id = uuid4()

    uow.customers.add(
        Customer(
            tenant_id=first_tenant_id,
            name="First Tenant Customer",
            code="ACME-001",
            status=CustomerStatus.ACTIVE,
        )
    )

    use_case = CreateCustomer(uow)

    customer = await use_case.execute(
        CreateCustomerCommand(
            tenant_id=second_tenant_id,
            name="Second Tenant Customer",
            code="ACME-001",
        )
    )

    assert customer.tenant_id == second_tenant_id
    assert customer.code == "ACME-001"

    assert len(uow.customers.customers) == 2
    assert uow.committed is True
