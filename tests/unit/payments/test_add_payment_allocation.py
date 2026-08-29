from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.billing.domain.enums import InvoiceStatus
from app.modules.billing.infrastructure.models.invoice import Invoice
from app.modules.payments.application.use_cases.add_payment_allocation import (
    AddPaymentAllocationUseCase,
)
from app.modules.payments.domain.enums import PaymentMethod, PaymentStatus
from app.modules.payments.domain.exceptions import (
    DuplicatePaymentAllocationError,
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


@pytest.mark.asyncio
async def test_add_payment_allocation() -> None:
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
    )

    unit_of_work.fake_payments.items.append(payment)
    unit_of_work.fake_invoices.items.append(invoice)

    use_case = AddPaymentAllocationUseCase(unit_of_work)

    allocation = await use_case.execute(
        tenant_id=tenant_id,
        payment_id=payment.id,
        invoice_id=invoice.id,
        amount=Decimal("40.00"),
    )

    assert allocation.tenant_id == tenant_id
    assert allocation.payment_id == payment.id
    assert allocation.invoice_id == invoice.id
    assert allocation.amount == Decimal("40.00")

    assert unit_of_work.fake_payment_allocations.items == [allocation]
    assert unit_of_work.committed is True


@pytest.mark.asyncio
async def test_add_allocation_rejects_missing_payment() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    invoice = make_invoice(
        tenant_id=tenant_id,
        customer_id=customer_id,
    )

    unit_of_work.fake_invoices.items.append(invoice)

    use_case = AddPaymentAllocationUseCase(unit_of_work)

    with pytest.raises(PaymentNotFoundError):
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=uuid4(),
            invoice_id=invoice.id,
            amount=Decimal("10.00"),
        )


@pytest.mark.asyncio
async def test_add_allocation_requires_draft_payment() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
        status=PaymentStatus.POSTED,
    )

    unit_of_work.fake_payments.items.append(payment)

    use_case = AddPaymentAllocationUseCase(unit_of_work)

    with pytest.raises(InvalidPaymentStateTransitionError):
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment.id,
            invoice_id=uuid4(),
            amount=Decimal("10.00"),
        )


@pytest.mark.asyncio
async def test_add_allocation_requires_issued_invoice() -> None:
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

    unit_of_work.fake_payments.items.append(payment)
    unit_of_work.fake_invoices.items.append(invoice)

    use_case = AddPaymentAllocationUseCase(unit_of_work)

    with pytest.raises(InvalidInvoiceForPaymentError):
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment.id,
            invoice_id=invoice.id,
            amount=Decimal("10.00"),
        )


@pytest.mark.asyncio
async def test_add_allocation_requires_matching_currency() -> None:
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

    unit_of_work.fake_payments.items.append(payment)
    unit_of_work.fake_invoices.items.append(invoice)

    use_case = AddPaymentAllocationUseCase(unit_of_work)

    with pytest.raises(PaymentCurrencyMismatchError):
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment.id,
            invoice_id=invoice.id,
            amount=Decimal("10.00"),
        )


@pytest.mark.asyncio
async def test_add_allocation_rejects_duplicate_invoice() -> None:
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
    )

    existing_allocation = PaymentAllocation(
        id=uuid4(),
        tenant_id=tenant_id,
        payment_id=payment.id,
        invoice_id=invoice.id,
        amount=Decimal("20.00"),
    )

    unit_of_work.fake_payments.items.append(payment)
    unit_of_work.fake_invoices.items.append(invoice)
    unit_of_work.fake_payment_allocations.items.append(existing_allocation)

    use_case = AddPaymentAllocationUseCase(unit_of_work)

    with pytest.raises(DuplicatePaymentAllocationError):
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment.id,
            invoice_id=invoice.id,
            amount=Decimal("10.00"),
        )


@pytest.mark.asyncio
async def test_add_allocation_cannot_exceed_payment_amount() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
        amount=Decimal("50.00"),
    )

    first_invoice = make_invoice(
        tenant_id=tenant_id,
        customer_id=customer_id,
    )

    second_invoice = make_invoice(
        tenant_id=tenant_id,
        customer_id=customer_id,
    )

    existing_allocation = PaymentAllocation(
        id=uuid4(),
        tenant_id=tenant_id,
        payment_id=payment.id,
        invoice_id=first_invoice.id,
        amount=Decimal("40.00"),
    )

    unit_of_work.fake_payments.items.append(payment)
    unit_of_work.fake_invoices.items.extend(
        [
            first_invoice,
            second_invoice,
        ]
    )
    unit_of_work.fake_payment_allocations.items.append(existing_allocation)

    use_case = AddPaymentAllocationUseCase(unit_of_work)

    with pytest.raises(PaymentAllocationExceedsPaymentError):
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment.id,
            invoice_id=second_invoice.id,
            amount=Decimal("20.00"),
        )


@pytest.mark.asyncio
async def test_add_allocation_cannot_exceed_invoice_total() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    current_payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
        amount=Decimal("100.00"),
    )

    posted_payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
        amount=Decimal("80.00"),
        status=PaymentStatus.POSTED,
    )

    invoice = make_invoice(
        tenant_id=tenant_id,
        customer_id=customer_id,
        total_amount=Decimal("100.00"),
    )

    existing_allocation = PaymentAllocation(
        id=uuid4(),
        tenant_id=tenant_id,
        payment_id=posted_payment.id,
        invoice_id=invoice.id,
        amount=Decimal("80.00"),
    )

    unit_of_work.fake_payments.items.extend(
        [
            current_payment,
            posted_payment,
        ]
    )
    unit_of_work.fake_invoices.items.append(invoice)
    unit_of_work.fake_payment_allocations.items.append(existing_allocation)

    use_case = AddPaymentAllocationUseCase(unit_of_work)

    with pytest.raises(PaymentAllocationExceedsInvoiceError):
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=current_payment.id,
            invoice_id=invoice.id,
            amount=Decimal("30.00"),
        )


@pytest.mark.asyncio
async def test_add_allocation_ignores_other_draft_allocations_for_invoice_capacity() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    current_payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
        amount=Decimal("100.00"),
    )

    other_draft_payment = make_payment(
        tenant_id=tenant_id,
        customer_id=customer_id,
        amount=Decimal("100.00"),
        status=PaymentStatus.DRAFT,
    )

    invoice = make_invoice(
        tenant_id=tenant_id,
        customer_id=customer_id,
        total_amount=Decimal("100.00"),
    )

    other_draft_allocation = PaymentAllocation(
        id=uuid4(),
        tenant_id=tenant_id,
        payment_id=other_draft_payment.id,
        invoice_id=invoice.id,
        amount=Decimal("100.00"),
    )

    unit_of_work.fake_payments.items.extend(
        [
            current_payment,
            other_draft_payment,
        ]
    )
    unit_of_work.fake_invoices.items.append(invoice)
    unit_of_work.fake_payment_allocations.items.append(other_draft_allocation)

    use_case = AddPaymentAllocationUseCase(unit_of_work)

    allocation = await use_case.execute(
        tenant_id=tenant_id,
        payment_id=current_payment.id,
        invoice_id=invoice.id,
        amount=Decimal("100.00"),
    )

    assert allocation.payment_id == current_payment.id
    assert allocation.invoice_id == invoice.id
    assert allocation.amount == Decimal("100.00")
    assert unit_of_work.committed is True
