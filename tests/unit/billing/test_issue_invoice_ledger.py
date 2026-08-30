from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.billing.application.use_cases.issue_invoice import (
    IssueInvoiceUseCase,
)
from app.modules.billing.domain.enums import InvoiceStatus
from app.modules.billing.infrastructure.models.invoice import Invoice
from app.modules.billing.infrastructure.models.invoice_line import InvoiceLine
from app.modules.ledger.application.exceptions import (
    LedgerAccountInactiveError,
)
from app.modules.ledger.domain.enums import (
    JournalSourceType,
    LedgerAccountPurpose,
    LedgerAccountStatus,
    LedgerAccountType,
)
from app.modules.ledger.infrastructure.models import LedgerAccount
from tests.unit.billing.fakes import FakeBillingUnitOfWork

pytestmark = pytest.mark.asyncio


def add_ledger_account(
    uow: FakeBillingUnitOfWork,
    *,
    tenant_id: UUID,
    code: str,
    name: str,
    account_type: LedgerAccountType,
    purpose: LedgerAccountPurpose,
) -> LedgerAccount:
    account = LedgerAccount(
        id=uuid4(),
        tenant_id=tenant_id,
        code=code,
        name=name,
        type=account_type.value,
        purpose=purpose.value,
        status=LedgerAccountStatus.ACTIVE.value,
    )

    uow.fake_ledger_accounts.items.append(account)

    return account


async def test_issue_invoice_posts_balanced_journal_without_tax() -> None:
    tenant_id = uuid4()
    invoice_id = uuid4()
    actor_id = uuid4()

    uow = FakeBillingUnitOfWork()

    invoice = Invoice(
        id=invoice_id,
        tenant_id=tenant_id,
        customer_id=uuid4(),
        invoice_number="INV-001",
        status=InvoiceStatus.DRAFT.value,
        currency="USD",
        subtotal=Decimal("100.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("100.00"),
    )

    uow.fake_invoices.items.append(invoice)

    uow.fake_invoice_lines.items.append(
        InvoiceLine(
            id=uuid4(),
            tenant_id=tenant_id,
            invoice_id=invoice_id,
        )
    )

    accounts_receivable = add_ledger_account(
        uow,
        tenant_id=tenant_id,
        code="1100",
        name="Accounts Receivable",
        account_type=LedgerAccountType.ASSET,
        purpose=LedgerAccountPurpose.ACCOUNTS_RECEIVABLE,
    )

    revenue = add_ledger_account(
        uow,
        tenant_id=tenant_id,
        code="4000",
        name="Revenue",
        account_type=LedgerAccountType.REVENUE,
        purpose=LedgerAccountPurpose.REVENUE,
    )

    use_case = IssueInvoiceUseCase(uow)

    result = await use_case.execute(
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        actor_id=actor_id,
    )

    assert result.status == InvoiceStatus.ISSUED.value
    assert result.issued_at is not None
    assert uow.committed is True

    assert len(uow.fake_journal_entries.items) == 1
    assert len(uow.fake_journal_lines.items) == 2

    entry = uow.fake_journal_entries.items[0]

    assert entry.tenant_id == tenant_id
    assert entry.source_type == JournalSourceType.INVOICE_ISSUED.value
    assert entry.source_id == invoice_id

    debit_line = next(
        line
        for line in uow.fake_journal_lines.items
        if line.ledger_account_id == accounts_receivable.id
    )

    revenue_line = next(
        line for line in uow.fake_journal_lines.items if line.ledger_account_id == revenue.id
    )

    assert debit_line.debit == Decimal("100.00")
    assert debit_line.credit == Decimal("0.00")

    assert revenue_line.debit == Decimal("0.00")
    assert revenue_line.credit == Decimal("100.00")


async def test_issue_invoice_posts_tax_payable_line() -> None:
    tenant_id = uuid4()
    invoice_id = uuid4()
    actor_id = uuid4()

    uow = FakeBillingUnitOfWork()

    invoice = Invoice(
        id=invoice_id,
        tenant_id=tenant_id,
        customer_id=uuid4(),
        invoice_number="INV-002",
        status=InvoiceStatus.DRAFT.value,
        currency="USD",
        subtotal=Decimal("100.00"),
        tax_amount=Decimal("15.00"),
        total_amount=Decimal("115.00"),
    )

    uow.fake_invoices.items.append(invoice)

    uow.fake_invoice_lines.items.append(
        InvoiceLine(
            id=uuid4(),
            tenant_id=tenant_id,
            invoice_id=invoice_id,
        )
    )

    accounts_receivable = add_ledger_account(
        uow,
        tenant_id=tenant_id,
        code="1100",
        name="Accounts Receivable",
        account_type=LedgerAccountType.ASSET,
        purpose=LedgerAccountPurpose.ACCOUNTS_RECEIVABLE,
    )

    revenue = add_ledger_account(
        uow,
        tenant_id=tenant_id,
        code="4000",
        name="Revenue",
        account_type=LedgerAccountType.REVENUE,
        purpose=LedgerAccountPurpose.REVENUE,
    )

    tax_payable = add_ledger_account(
        uow,
        tenant_id=tenant_id,
        code="2100",
        name="Tax Payable",
        account_type=LedgerAccountType.LIABILITY,
        purpose=LedgerAccountPurpose.TAX_PAYABLE,
    )

    use_case = IssueInvoiceUseCase(uow)

    result = await use_case.execute(
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        actor_id=actor_id,
    )

    assert result.status == InvoiceStatus.ISSUED.value
    assert uow.committed is True

    assert len(uow.fake_journal_entries.items) == 1
    assert len(uow.fake_journal_lines.items) == 3

    lines_by_account = {line.ledger_account_id: line for line in uow.fake_journal_lines.items}

    ar_line = lines_by_account[accounts_receivable.id]
    revenue_line = lines_by_account[revenue.id]
    tax_line = lines_by_account[tax_payable.id]

    assert ar_line.debit == Decimal("115.00")
    assert ar_line.credit == Decimal("0.00")

    assert revenue_line.debit == Decimal("0.00")
    assert revenue_line.credit == Decimal("100.00")

    assert tax_line.debit == Decimal("0.00")
    assert tax_line.credit == Decimal("15.00")


async def test_issue_invoice_rolls_back_when_ledger_posting_fails() -> None:
    tenant_id = uuid4()
    invoice_id = uuid4()
    actor_id = uuid4()

    uow = FakeBillingUnitOfWork()

    invoice = Invoice(
        id=invoice_id,
        tenant_id=tenant_id,
        customer_id=uuid4(),
        invoice_number="INV-003",
        status=InvoiceStatus.DRAFT.value,
        currency="USD",
        subtotal=Decimal("100.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("100.00"),
    )

    uow.fake_invoices.items.append(invoice)

    uow.fake_invoice_lines.items.append(
        InvoiceLine(
            id=uuid4(),
            tenant_id=tenant_id,
            invoice_id=invoice_id,
        )
    )

    accounts_receivable = add_ledger_account(
        uow,
        tenant_id=tenant_id,
        code="1100",
        name="Accounts Receivable",
        account_type=LedgerAccountType.ASSET,
        purpose=LedgerAccountPurpose.ACCOUNTS_RECEIVABLE,
    )

    accounts_receivable.status = LedgerAccountStatus.INACTIVE.value

    add_ledger_account(
        uow,
        tenant_id=tenant_id,
        code="4000",
        name="Revenue",
        account_type=LedgerAccountType.REVENUE,
        purpose=LedgerAccountPurpose.REVENUE,
    )

    use_case = IssueInvoiceUseCase(uow)

    with pytest.raises(LedgerAccountInactiveError):
        await use_case.execute(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            actor_id=actor_id,
        )

    assert uow.committed is False
    assert uow.rolled_back is True

    assert len(uow.fake_journal_entries.items) == 0
    assert len(uow.fake_journal_lines.items) == 0
    assert uow.fake_audit_logs.items == []
