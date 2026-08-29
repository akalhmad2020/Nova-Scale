from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.customers.infrastructure.models.customer import Customer
from app.modules.payments.application.use_cases.create_payment import (
    CreatePaymentUseCase,
)
from app.modules.payments.domain.enums import PaymentMethod, PaymentStatus
from app.modules.payments.domain.exceptions import (
    DuplicatePaymentNumberError,
    PaymentCustomerNotFoundError,
)
from app.modules.payments.infrastructure.models.payment import Payment
from tests.unit.payments.fakes import FakePaymentsUnitOfWork


@pytest.mark.asyncio
async def test_create_payment() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    customer = Customer(
        id=customer_id,
        tenant_id=tenant_id,
        code="CUST-001",
        name="Test Customer",
    )
    unit_of_work.fake_customers.items.append(customer)

    use_case = CreatePaymentUseCase(unit_of_work)

    payment = await use_case.execute(
        tenant_id=tenant_id,
        customer_id=customer_id,
        payment_number="PAY-001",
        currency="USD",
        amount=Decimal("100.00"),
        method=PaymentMethod.BANK_TRANSFER,
        reference="BANK-REF-001",
    )

    assert payment.tenant_id == tenant_id
    assert payment.customer_id == customer_id
    assert payment.payment_number == "PAY-001"
    assert payment.currency == "USD"
    assert payment.amount == Decimal("100.00")
    assert payment.method == PaymentMethod.BANK_TRANSFER
    assert payment.status == PaymentStatus.DRAFT
    assert payment.reference == "BANK-REF-001"
    assert payment.posted_at is None

    assert unit_of_work.fake_payments.items == [payment]
    assert unit_of_work.committed is True


@pytest.mark.asyncio
async def test_create_payment_rejects_customer_from_another_tenant() -> None:
    customer_tenant_id = uuid4()
    requested_tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    customer = Customer(
        id=customer_id,
        tenant_id=customer_tenant_id,
        code="CUST-001",
        name="Test Customer",
    )
    unit_of_work.fake_customers.items.append(customer)

    use_case = CreatePaymentUseCase(unit_of_work)

    with pytest.raises(PaymentCustomerNotFoundError):
        await use_case.execute(
            tenant_id=requested_tenant_id,
            customer_id=customer_id,
            payment_number="PAY-001",
            currency="USD",
            amount=Decimal("100.00"),
            method=PaymentMethod.BANK_TRANSFER,
        )

    assert unit_of_work.fake_payments.items == []
    assert unit_of_work.committed is False


@pytest.mark.asyncio
async def test_create_payment_rejects_duplicate_payment_number() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    customer = Customer(
        id=customer_id,
        tenant_id=tenant_id,
        code="CUST-001",
        name="Test Customer",
    )
    unit_of_work.fake_customers.items.append(customer)

    existing_payment = Payment(
        id=uuid4(),
        tenant_id=tenant_id,
        customer_id=customer_id,
        payment_number="PAY-001",
        status=PaymentStatus.DRAFT,
        currency="USD",
        amount=Decimal("100.00"),
        method=PaymentMethod.BANK_TRANSFER,
    )
    unit_of_work.fake_payments.items.append(existing_payment)

    use_case = CreatePaymentUseCase(unit_of_work)

    with pytest.raises(DuplicatePaymentNumberError):
        await use_case.execute(
            tenant_id=tenant_id,
            customer_id=customer_id,
            payment_number="PAY-001",
            currency="USD",
            amount=Decimal("50.00"),
            method=PaymentMethod.CASH,
        )

    assert unit_of_work.fake_payments.items == [existing_payment]
    assert unit_of_work.committed is False
