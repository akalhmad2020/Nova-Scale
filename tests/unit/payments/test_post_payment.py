from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.audit.domain.enums import AuditActorType, AuditOutcome
from app.modules.billing.domain.enums import InvoiceStatus
from app.modules.billing.infrastructure.models.invoice import Invoice
from app.modules.ledger.application.exceptions import (
    LedgerAccountInactiveError,
    LedgerAccountNotFoundError,
)
from app.modules.ledger.domain.enums import (
    JournalSourceType,
    LedgerAccountPurpose,
    LedgerAccountStatus,
    LedgerAccountType,
)
from app.modules.ledger.infrastructure.models import LedgerAccount
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
    PaymentNotFullyAllocatedError,
)
from app.modules.payments.infrastructure.models.payment import Payment
from app.modules.payments.infrastructure.models.payment_allocation import (
    PaymentAllocation,
)
from tests.unit.payments.fakes import FakePaymentsUnitOfWork


def make_ledger_account(
    *,
    tenant_id: UUID,
    code: str,
    name: str,
    account_type: LedgerAccountType,
    purpose: LedgerAccountPurpose,
    status: LedgerAccountStatus = LedgerAccountStatus.ACTIVE,
) -> LedgerAccount:
    return LedgerAccount(
        id=uuid4(),
        tenant_id=tenant_id,
        code=code,
        name=name,
        type=account_type.value,
        purpose=purpose.value,
        status=status.value,
    )


def add_payment_ledger_accounts(
    unit_of_work: FakePaymentsUnitOfWork,
    *,
    tenant_id: UUID,
) -> tuple[LedgerAccount, LedgerAccount]:
    cash = make_ledger_account(
        tenant_id=tenant_id,
        code="1000",
        name="Cash",
        account_type=LedgerAccountType.ASSET,
        purpose=LedgerAccountPurpose.CASH,
    )

    accounts_receivable = make_ledger_account(
        tenant_id=tenant_id,
        code="1100",
        name="Accounts Receivable",
        account_type=LedgerAccountType.ASSET,
        purpose=LedgerAccountPurpose.ACCOUNTS_RECEIVABLE,
    )

    unit_of_work.fake_ledger_accounts.items.extend(
        [
            cash,
            accounts_receivable,
        ]
    )

    return cash, accounts_receivable


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
    actor_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    add_payment_ledger_accounts(
        unit_of_work,
        tenant_id=tenant_id,
    )

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
        actor_id=actor_id,
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
    actor_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    add_payment_ledger_accounts(
        unit_of_work,
        tenant_id=tenant_id,
    )

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
        actor_id=actor_id,
    )

    assert payment.status == PaymentStatus.POSTED
    assert payment.posted_at is not None

    assert invoice.status == InvoiceStatus.PAID
    assert invoice.paid_at is not None

    assert unit_of_work.committed is True


@pytest.mark.asyncio
async def test_post_payment_records_user_audit_log() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()
    actor_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    add_payment_ledger_accounts(
        unit_of_work,
        tenant_id=tenant_id,
    )

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
        actor_id=actor_id,
    )

    assert len(unit_of_work.fake_audit_logs.items) == 1

    audit_log = unit_of_work.fake_audit_logs.items[0]

    assert audit_log.tenant_id == tenant_id
    assert audit_log.actor_type == AuditActorType.USER
    assert audit_log.actor_id == actor_id

    assert audit_log.action == "payment.posted"

    assert audit_log.resource_type == "payment"
    assert audit_log.resource_id == payment.id

    assert audit_log.outcome == AuditOutcome.SUCCESS

    assert audit_log.metadata_ == {
        "payment_number": payment.payment_number,
        "amount": str(payment.amount),
        "currency": payment.currency,
    }

    assert audit_log.occurred_at == payment.posted_at
    assert unit_of_work.committed is True


@pytest.mark.asyncio
async def test_post_payment_marks_invoice_paid_using_previous_posted_payment() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()
    actor_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    add_payment_ledger_accounts(
        unit_of_work,
        tenant_id=tenant_id,
    )

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
        actor_id=actor_id,
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
            actor_id=uuid4(),
        )

    assert unit_of_work.committed is False
    assert unit_of_work.fake_audit_logs.items == []


@pytest.mark.asyncio
async def test_post_payment_requires_draft_status() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()
    actor_id = uuid4()

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
            actor_id=actor_id,
        )

    assert unit_of_work.committed is False
    assert unit_of_work.fake_audit_logs.items == []


@pytest.mark.asyncio
async def test_post_payment_requires_at_least_one_allocation() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()
    actor_id = uuid4()

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
            actor_id=actor_id,
        )

    assert payment.status == PaymentStatus.DRAFT
    assert unit_of_work.committed is False
    assert unit_of_work.fake_audit_logs.items == []


@pytest.mark.asyncio
async def test_post_payment_rejects_allocation_total_above_payment_amount() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()
    actor_id = uuid4()

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
            actor_id=actor_id,
        )

    assert payment.status == PaymentStatus.DRAFT
    assert unit_of_work.committed is False
    assert unit_of_work.fake_audit_logs.items == []


@pytest.mark.asyncio
async def test_post_payment_rejects_payment_that_is_not_fully_allocated() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()
    actor_id = uuid4()

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
        amount=Decimal("60.00"),
    )

    unit_of_work.fake_payments.items.append(payment)
    unit_of_work.fake_invoices.items.append(invoice)
    unit_of_work.fake_payment_allocations.items.append(allocation)

    use_case = PostPaymentUseCase(unit_of_work)

    with pytest.raises(PaymentNotFullyAllocatedError):
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment.id,
            actor_id=actor_id,
        )

    assert payment.status == PaymentStatus.DRAFT
    assert payment.posted_at is None
    assert invoice.status == InvoiceStatus.ISSUED
    assert invoice.paid_at is None
    assert unit_of_work.committed is False
    assert unit_of_work.fake_audit_logs.items == []


@pytest.mark.asyncio
async def test_post_payment_rejects_invalid_invoice() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()
    actor_id = uuid4()

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
            actor_id=actor_id,
        )

    assert payment.status == PaymentStatus.DRAFT
    assert unit_of_work.committed is False
    assert unit_of_work.fake_audit_logs.items == []


@pytest.mark.asyncio
async def test_post_payment_rejects_currency_mismatch() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()
    actor_id = uuid4()

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
            actor_id=actor_id,
        )

    assert payment.status == PaymentStatus.DRAFT
    assert unit_of_work.committed is False
    assert unit_of_work.fake_audit_logs.items == []


@pytest.mark.asyncio
async def test_post_payment_rejects_invoice_overpayment() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()
    actor_id = uuid4()

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
            actor_id=actor_id,
        )

    assert current_payment.status == PaymentStatus.DRAFT
    assert invoice.status == InvoiceStatus.ISSUED
    assert unit_of_work.committed is False
    assert unit_of_work.fake_audit_logs.items == []


@pytest.mark.asyncio
async def test_post_payment_creates_balanced_ledger_journal() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()
    actor_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    cash, accounts_receivable = add_payment_ledger_accounts(
        unit_of_work,
        tenant_id=tenant_id,
    )

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
        actor_id=actor_id,
    )

    assert len(unit_of_work.fake_journal_entries.items) == 1

    entry = unit_of_work.fake_journal_entries.items[0]

    assert entry.tenant_id == tenant_id
    assert entry.source_type == JournalSourceType.PAYMENT_POSTED.value
    assert entry.source_id == payment.id

    journal_lines = unit_of_work.fake_journal_lines.items

    assert len(journal_lines) == 2

    cash_line = next(line for line in journal_lines if line.ledger_account_id == cash.id)
    receivable_line = next(
        line for line in journal_lines if line.ledger_account_id == accounts_receivable.id
    )

    assert cash_line.debit == Decimal("100.00")
    assert cash_line.credit == Decimal("0.00")

    assert receivable_line.debit == Decimal("0.00")
    assert receivable_line.credit == Decimal("100.00")

    total_debit = sum(
        (line.debit for line in journal_lines),
        Decimal("0.00"),
    )
    total_credit = sum(
        (line.credit for line in journal_lines),
        Decimal("0.00"),
    )

    assert total_debit == Decimal("100.00")
    assert total_credit == Decimal("100.00")
    assert total_debit == total_credit

    assert payment.status == PaymentStatus.POSTED
    assert invoice.status == InvoiceStatus.PAID
    assert unit_of_work.committed is True


@pytest.mark.asyncio
async def test_post_payment_rolls_back_when_cash_account_is_missing() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()
    actor_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    accounts_receivable = make_ledger_account(
        tenant_id=tenant_id,
        code="1100",
        name="Accounts Receivable",
        account_type=LedgerAccountType.ASSET,
        purpose=LedgerAccountPurpose.ACCOUNTS_RECEIVABLE,
    )
    unit_of_work.fake_ledger_accounts.items.append(accounts_receivable)

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

    with pytest.raises(LedgerAccountNotFoundError):
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment.id,
            actor_id=actor_id,
        )

    assert payment.status == PaymentStatus.DRAFT
    assert payment.posted_at is None
    assert invoice.status == InvoiceStatus.ISSUED
    assert invoice.paid_at is None
    assert unit_of_work.fake_journal_entries.items == []
    assert unit_of_work.fake_journal_lines.items == []
    assert unit_of_work.fake_audit_logs.items == []
    assert unit_of_work.committed is False
    assert unit_of_work.rolled_back is True


@pytest.mark.asyncio
async def test_post_payment_rolls_back_when_accounts_receivable_is_inactive() -> None:
    tenant_id = uuid4()
    customer_id = uuid4()
    actor_id = uuid4()

    unit_of_work = FakePaymentsUnitOfWork()

    cash = make_ledger_account(
        tenant_id=tenant_id,
        code="1000",
        name="Cash",
        account_type=LedgerAccountType.ASSET,
        purpose=LedgerAccountPurpose.CASH,
    )
    accounts_receivable = make_ledger_account(
        tenant_id=tenant_id,
        code="1100",
        name="Accounts Receivable",
        account_type=LedgerAccountType.ASSET,
        purpose=LedgerAccountPurpose.ACCOUNTS_RECEIVABLE,
        status=LedgerAccountStatus.INACTIVE,
    )

    unit_of_work.fake_ledger_accounts.items.extend(
        [
            cash,
            accounts_receivable,
        ]
    )

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

    with pytest.raises(LedgerAccountInactiveError):
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment.id,
            actor_id=actor_id,
        )

    assert payment.status == PaymentStatus.DRAFT
    assert payment.posted_at is None
    assert invoice.status == InvoiceStatus.ISSUED
    assert invoice.paid_at is None
    assert unit_of_work.fake_journal_entries.items == []
    assert unit_of_work.fake_journal_lines.items == []
    assert unit_of_work.fake_audit_logs.items == []
    assert unit_of_work.committed is False
    assert unit_of_work.rolled_back is True
