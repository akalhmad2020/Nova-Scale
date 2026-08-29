from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.billing.domain.enums import InvoiceStatus
from app.modules.billing.infrastructure.models.invoice import Invoice
from app.modules.payments.application.use_cases.post_payment import (
    PostPaymentUseCase,
)
from app.modules.payments.domain.enums import PaymentMethod, PaymentStatus
from app.modules.payments.domain.exceptions import (
    InvalidInvoiceForPaymentError,
    InvalidPaymentStateTransitionError,
    PaymentAllocationExceedsInvoiceError,
    PaymentAllocationExceedsPaymentError,
    PaymentCurrencyMismatchError,
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
    amount: Decimal = Decimal("100.00"),
    currency: str = "USD",
    status: PaymentStatus = PaymentStatus.DRAFT,
) -> Payment:
    return Payment(
        id=uuid4(),
        tenant_id=tenant_id,
        customer_id=customer_id,
        payment_number=f"PAY-{uuid4()}",
        status=status,
        currency=currency,
        amount=amount,
        method=PaymentMethod.BANK_TRANSFER,
    )


def make_invoice(
    *,
    tenant_id: UUID,
    customer_id: UUID,
    total_amount: Decimal = Decimal("100.00"),
    currency: str = "USD",
    status: InvoiceStatus = InvoiceStatus.ISSUED,
) -> Invoice:
    return Invoice(
        id=uuid4(),
        tenant_id=tenant_id,
        customer_id=customer_id,
        invoice_number=f"INV-{uuid4()}",
        status=status,
        currency=currency,
        subtotal=total_amount,
        tax_amount=Decimal("0.00"),
        total_amount=total_amount,
    )


def make_allocation(
    *,
    tenant_id: UUID,
    payment_id: UUID,
    invoice_id: UUID,
    amount: Decimal,
) -> PaymentAllocation:
    return PaymentAllocation(
        id=uuid4(),
        tenant_id=tenant_id,
        payment_id=payment_id,
        invoice_id=invoice_id,
        amount=amount,
    )


@pytest.mark.asyncio
async def test_post_partial_payment_keeps_invoice_issued() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
        amount=Decimal("40.00"),
    )
    invoice = make_invoice(
        tenant_id=tenant_id,
        customer_id=customer_id,
        total_amount=Decimal("100.00"),
    )
    allocation = make_allocation(
        tenant_id=tenant_id,
        payment_id=payment.id,
        invoice_id=invoice.id,
        amount=Decimal("40.00"),
    )

    unit_of_work.fake_payments.items.append(payment)
    unit_of_work.fake_invoices.items.append(invoice)
    unit_of_work.fake_payment_allocations.items.append(allocation)

    use_case = PostPaymentUseCase(unit_of_work)

    result = await use_case.execute(
        tenant_id=tenant_id,
        payment_id=payment.id,
    )

    assert result.status == PaymentStatus.POSTED
    assert result.posted_at is not None

    assert invoice.status == InvoiceStatus.ISSUED
    assert invoice.paid_at is None

    assert unit_of_work.committed is True


@pytest.mark.asyncio
async def test_post_payment_marks_fully_paid_invoice_as_paid() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
        amount=Decimal("100.00"),
    )
    invoice = make_invoice(
        tenant_id=tenant_id,
        customer_id=customer_id,
        total_amount=Decimal("100.00"),
    )
    allocation = make_allocation(
        tenant_id=tenant_id,
        payment_id=payment.id,
        invoice_id=invoice.id,
        amount=Decimal("100.00"),
    )

    unit_of_work.fake_payments.items.append(payment)
    unit_of_work.fake_invoices.items.append(invoice)
    unit_of_work.fake_payment_allocations.items.append(allocation)

    use_case = PostPaymentUseCase(unit_of_work)

    await use_case.execute(
        tenant_id=tenant_id,
        payment_id=payment.id,
    )

    assert payment.status == PaymentStatus.POSTED
    assert payment.posted_at is not None

    assert invoice.status == InvoiceStatus.PAID
    assert invoice.paid_at is not None

    assert unit_of_work.committed is True


@pytest.mark.asyncio
async def test_post_payment_marks_invoice_paid_using_previous_posted_payment() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    previous_payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
        amount=Decimal("40.00"),
        status=PaymentStatus.POSTED,
    )
    current_payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
        amount=Decimal("60.00"),
    )
    invoice = make_invoice(
        tenant_id=tenant_id,
        customer_id=customer_id,
        total_amount=Decimal("100.00"),
    )

    previous_allocation = make_allocation(
        tenant_id=tenant_id,
        payment_id=previous_payment.id,
        invoice_id=invoice.id,
        amount=Decimal("40.00"),
    )
    current_allocation = make_allocation(
        tenant_id=tenant_id,
        payment_id=current_payment.id,
        invoice_id=invoice.id,
        amount=Decimal("60.00"),
    )

    unit_of_work.fake_payments.items.extend([previous_payment, current_payment])
    unit_of_work.fake_invoices.items.append(invoice)
    unit_of_work.fake_payment_allocations.items.extend([previous_allocation, current_allocation])

    use_case = PostPaymentUseCase(unit_of_work)

    await use_case.execute(
        tenant_id=tenant_id,
        payment_id=current_payment.id,
    )

    assert current_payment.status == PaymentStatus.POSTED
    assert invoice.status == InvoiceStatus.PAID
    assert invoice.paid_at is not None


@pytest.mark.asyncio
async def test_post_payment_rejects_missing_payment() -> None:
    unit_of_work = FakePaymentsUnitOfWork()

    use_case = PostPaymentUseCase(unit_of_work)

    with pytest.raises(PaymentNotFoundError):
        await use_case.execute(
            tenant_id=uuid4(),
            payment_id=uuid4(),
        )

    assert unit_of_work.committed is False


@pytest.mark.asyncio
async def test_post_payment_requires_draft_status() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
        status=PaymentStatus.POSTED,
    )
    unit_of_work.fake_payments.items.append(payment)

    use_case = PostPaymentUseCase(unit_of_work)

    with pytest.raises(InvalidPaymentStateTransitionError):
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment.id,
        )

    assert unit_of_work.committed is False


@pytest.mark.asyncio
async def test_post_payment_requires_at_least_one_allocation() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
    )
    unit_of_work.fake_payments.items.append(payment)

    use_case = PostPaymentUseCase(unit_of_work)

    with pytest.raises(InvalidPaymentStateTransitionError):
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment.id,
        )

    assert payment.status == PaymentStatus.DRAFT
    assert unit_of_work.committed is False


@pytest.mark.asyncio
async def test_post_payment_rejects_allocation_total_above_payment_amount() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
        amount=Decimal("50.00"),
    )
    invoice = make_invoice(
        tenant_id=tenant_id,
        customer_id=customer_id,
        total_amount=Decimal("100.00"),
    )
    allocation = make_allocation(
        tenant_id=tenant_id,
        payment_id=payment.id,
        invoice_id=invoice.id,
        amount=Decimal("60.00"),
    )

    unit_of_work.fake_payments.items.append(payment)
    unit_of_work.fake_invoices.items.append(invoice)
    unit_of_work.fake_payment_allocations.items.append(allocation)

    use_case = PostPaymentUseCase(unit_of_work)

    with pytest.raises(PaymentAllocationExceedsPaymentError):
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment.id,
        )

    assert payment.status == PaymentStatus.DRAFT
    assert unit_of_work.committed is False


@pytest.mark.asyncio
async def test_post_payment_rejects_invalid_invoice() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
    )
    invoice = make_invoice(
        tenant_id=tenant_id,
        customer_id=customer_id,
        status=InvoiceStatus.DRAFT,
    )
    allocation = make_allocation(
        tenant_id=tenant_id,
        payment_id=payment.id,
        invoice_id=invoice.id,
        amount=Decimal("50.00"),
    )

    unit_of_work.fake_payments.items.append(payment)
    unit_of_work.fake_invoices.items.append(invoice)
    unit_of_work.fake_payment_allocations.items.append(allocation)

    use_case = PostPaymentUseCase(unit_of_work)

    with pytest.raises(InvalidInvoiceForPaymentError):
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment.id,
        )

    assert payment.status == PaymentStatus.DRAFT
    assert unit_of_work.committed is False


@pytest.mark.asyncio
async def test_post_payment_rejects_currency_mismatch() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
        currency="USD",
    )
    invoice = make_invoice(
        tenant_id=tenant_id,
        customer_id=customer_id,
        currency="EUR",
    )
    allocation = make_allocation(
        tenant_id=tenant_id,
        payment_id=payment.id,
        invoice_id=invoice.id,
        amount=Decimal("50.00"),
    )

    unit_of_work.fake_payments.items.append(payment)
    unit_of_work.fake_invoices.items.append(invoice)
    unit_of_work.fake_payment_allocations.items.append(allocation)

    use_case = PostPaymentUseCase(unit_of_work)

    with pytest.raises(PaymentCurrencyMismatchError):
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment.id,
        )

    assert payment.status == PaymentStatus.DRAFT
    assert unit_of_work.committed is False


@pytest.mark.asyncio
async def test_post_payment_rejects_invoice_overpayment() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    previous_payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
        amount=Decimal("80.00"),
        status=PaymentStatus.POSTED,
    )
    current_payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
        amount=Decimal("30.00"),
    )
    invoice = make_invoice(
        tenant_id=tenant_id,
        customer_id=customer_id,
        total_amount=Decimal("100.00"),
    )

    previous_allocation = make_allocation(
        tenant_id=tenant_id,
        payment_id=previous_payment.id,
        invoice_id=invoice.id,
        amount=Decimal("80.00"),
    )
    current_allocation = make_allocation(
        tenant_id=tenant_id,
        payment_id=current_payment.id,
        invoice_id=invoice.id,
        amount=Decimal("30.00"),
    )

    unit_of_work.fake_payments.items.extend([previous_payment, current_payment])
    unit_of_work.fake_invoices.items.append(invoice)
    unit_of_work.fake_payment_allocations.items.extend([previous_allocation, current_allocation])

    use_case = PostPaymentUseCase(unit_of_work)

    with pytest.raises(PaymentAllocationExceedsInvoiceError):
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=current_payment.id,
        )

    assert current_payment.status == PaymentStatus.DRAFT
    assert invoice.status == InvoiceStatus.ISSUED
    assert unit_of_work.committed is False
