from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.audit.domain.enums import AuditActorType, AuditOutcome
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
    actor_id = uuid4()

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
        actor_id=actor_id,
    )

    assert result.status == PaymentStatus.VOID
    assert payment.status == PaymentStatus.VOID
    assert unit_of_work.committed is True

    assert len(unit_of_work.fake_audit_logs.items) == 1

    audit_log = unit_of_work.fake_audit_logs.items[0]

    assert audit_log.tenant_id == tenant_id
    assert audit_log.actor_type == AuditActorType.USER
    assert audit_log.actor_id == actor_id

    assert audit_log.action == "payment.voided"

    assert audit_log.resource_type == "payment"
    assert audit_log.resource_id == payment.id

    assert audit_log.outcome == AuditOutcome.SUCCESS

    assert audit_log.metadata_ == {
        "payment_number": payment.payment_number,
        "amount": str(payment.amount),
        "currency": payment.currency,
    }


@pytest.mark.asyncio
async def test_void_payment_rejects_missing_payment() -> None:
    unit_of_work = FakePaymentsUnitOfWork()

    use_case = VoidPaymentUseCase(unit_of_work)

    with pytest.raises(PaymentNotFoundError):
        await use_case.execute(
            tenant_id=uuid4(),
            payment_id=uuid4(),
            actor_id=uuid4(),
        )

    assert unit_of_work.committed is False
    assert unit_of_work.fake_audit_logs.items == []


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
            actor_id=uuid4(),
        )

    assert payment.status == PaymentStatus.POSTED
    assert unit_of_work.committed is False
    assert unit_of_work.fake_audit_logs.items == []


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
            actor_id=uuid4(),
        )

    assert payment.status == PaymentStatus.VOID
    assert unit_of_work.committed is False
    assert unit_of_work.fake_audit_logs.items == []


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
            actor_id=uuid4(),
        )

    assert payment.status == PaymentStatus.DRAFT
    assert unit_of_work.committed is False
    assert unit_of_work.fake_audit_logs.items == []
