from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.payments.application.use_cases.void_payment import (
    VoidPaymentUseCase,
)
from app.modules.payments.domain.enums import PaymentMethod, PaymentStatus
from app.modules.payments.domain.exceptions import (
    InvalidPaymentStateTransitionError,
    PaymentNotFoundError,
)
from app.modules.payments.infrastructure.models.payment import Payment
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


@pytest.mark.asyncio
async def test_void_draft_payment() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
    )

    unit_of_work.fake_payments.items.append(payment)

    use_case = VoidPaymentUseCase(unit_of_work)

    result = await use_case.execute(
        tenant_id=tenant_id,
        payment_id=payment.id,
    )

    assert result.status == PaymentStatus.VOID
    assert payment.status == PaymentStatus.VOID
    assert unit_of_work.committed is True


@pytest.mark.asyncio
async def test_void_payment_rejects_missing_payment() -> None:
    unit_of_work = FakePaymentsUnitOfWork()

    use_case = VoidPaymentUseCase(unit_of_work)

    with pytest.raises(PaymentNotFoundError):
        await use_case.execute(
            tenant_id=uuid4(),
            payment_id=uuid4(),
        )

    assert unit_of_work.committed is False


@pytest.mark.asyncio
async def test_void_payment_rejects_posted_payment() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
        status=PaymentStatus.POSTED,
    )

    unit_of_work.fake_payments.items.append(payment)

    use_case = VoidPaymentUseCase(unit_of_work)

    with pytest.raises(InvalidPaymentStateTransitionError):
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment.id,
        )

    assert payment.status == PaymentStatus.POSTED
    assert unit_of_work.committed is False


@pytest.mark.asyncio
async def test_void_payment_rejects_already_void_payment() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
        status=PaymentStatus.VOID,
    )

    unit_of_work.fake_payments.items.append(payment)

    use_case = VoidPaymentUseCase(unit_of_work)

    with pytest.raises(InvalidPaymentStateTransitionError):
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment.id,
        )

    assert payment.status == PaymentStatus.VOID
    assert unit_of_work.committed is False


@pytest.mark.asyncio
async def test_void_payment_is_tenant_scoped() -> None:
    payment_tenant_id = uuid4()
    requested_tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    payment = make_payment(
        tenant_id=payment_tenant_id,
        customer_id=customer_id,
    )

    unit_of_work.fake_payments.items.append(payment)

    use_case = VoidPaymentUseCase(unit_of_work)

    with pytest.raises(PaymentNotFoundError):
        await use_case.execute(
            tenant_id=requested_tenant_id,
            payment_id=payment.id,
        )

    assert payment.status == PaymentStatus.DRAFT
    assert unit_of_work.committed is False
