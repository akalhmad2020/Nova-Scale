from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.payments.application.use_cases.remove_payment_allocation import (
    RemovePaymentAllocationUseCase,
)
from app.modules.payments.domain.enums import PaymentMethod, PaymentStatus
from app.modules.payments.domain.exceptions import (
    InvalidPaymentStateTransitionError,
    PaymentAllocationNotFoundError,
    PaymentNotFoundError,
)
from app.modules.payments.infrastructure.models.payment import Payment
from app.modules.payments.infrastructure.models.payment_allocation import (
    PaymentAllocation,
)
from tests.unit.payments.fakes import FakePaymentsUnitOfWork


def make_payment(
    *,
    tenant_id: UUID,
    customer_id: UUID,
    status: PaymentStatus = PaymentStatus.DRAFT,
) -> Payment:
    return Payment(
        id=uuid4(),
        tenant_id=tenant_id,
        customer_id=customer_id,
        payment_number=f"PAY-{uuid4()}",
        status=status,
        currency="USD",
        amount=Decimal("100.00"),
        method=PaymentMethod.BANK_TRANSFER,
    )


def make_allocation(
    *,
    tenant_id: UUID,
    payment_id: UUID,
    invoice_id: UUID,
) -> PaymentAllocation:
    return PaymentAllocation(
        id=uuid4(),
        tenant_id=tenant_id,
        payment_id=payment_id,
        invoice_id=invoice_id,
        amount=Decimal("40.00"),
    )


@pytest.mark.asyncio
async def test_remove_payment_allocation() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
    )

    allocation = make_allocation(
        tenant_id=tenant_id,
        payment_id=payment.id,
        invoice_id=uuid4(),
    )

    unit_of_work.fake_payments.items.append(payment)
    unit_of_work.fake_payment_allocations.items.append(allocation)

    use_case = RemovePaymentAllocationUseCase(unit_of_work)

    await use_case.execute(
        tenant_id=tenant_id,
        payment_id=payment.id,
        payment_allocation_id=allocation.id,
    )

    assert unit_of_work.fake_payment_allocations.items == []
    assert unit_of_work.committed is True


@pytest.mark.asyncio
async def test_remove_allocation_rejects_missing_payment() -> None:
    unit_of_work = FakePaymentsUnitOfWork()

    use_case = RemovePaymentAllocationUseCase(unit_of_work)

    with pytest.raises(PaymentNotFoundError):
        await use_case.execute(
            tenant_id=uuid4(),
            payment_id=uuid4(),
            payment_allocation_id=uuid4(),
        )

    assert unit_of_work.committed is False


@pytest.mark.asyncio
async def test_remove_allocation_requires_draft_payment() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
        status=PaymentStatus.POSTED,
    )

    allocation = make_allocation(
        tenant_id=tenant_id,
        payment_id=payment.id,
        invoice_id=uuid4(),
    )

    unit_of_work.fake_payments.items.append(payment)
    unit_of_work.fake_payment_allocations.items.append(allocation)

    use_case = RemovePaymentAllocationUseCase(unit_of_work)

    with pytest.raises(InvalidPaymentStateTransitionError):
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment.id,
            payment_allocation_id=allocation.id,
        )

    assert unit_of_work.fake_payment_allocations.items == [allocation]
    assert unit_of_work.committed is False


@pytest.mark.asyncio
async def test_remove_allocation_rejects_missing_allocation() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
    )

    unit_of_work.fake_payments.items.append(payment)

    use_case = RemovePaymentAllocationUseCase(unit_of_work)

    with pytest.raises(PaymentAllocationNotFoundError):
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment.id,
            payment_allocation_id=uuid4(),
        )

    assert unit_of_work.committed is False


@pytest.mark.asyncio
async def test_remove_allocation_rejects_allocation_from_another_payment() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
    )

    other_payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
    )

    allocation = make_allocation(
        tenant_id=tenant_id,
        payment_id=other_payment.id,
        invoice_id=uuid4(),
    )

    unit_of_work.fake_payments.items.extend([payment, other_payment])
    unit_of_work.fake_payment_allocations.items.append(allocation)

    use_case = RemovePaymentAllocationUseCase(unit_of_work)

    with pytest.raises(PaymentAllocationNotFoundError):
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment.id,
            payment_allocation_id=allocation.id,
        )

    assert unit_of_work.fake_payment_allocations.items == [allocation]
    assert unit_of_work.committed is False
