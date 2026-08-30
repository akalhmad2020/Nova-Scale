from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.billing.application.use_cases.issue_invoice import (
    INVOICE_ISSUED_EVENT_TYPE,
    IssueInvoiceUseCase,
)
from app.modules.billing.domain.enums import InvoiceStatus
from app.modules.billing.infrastructure.models.invoice import Invoice
from app.modules.billing.infrastructure.models.invoice_line import InvoiceLine
from app.modules.ledger.domain.enums import (
    LedgerAccountPurpose,
    LedgerAccountStatus,
    LedgerAccountType,
)
from app.modules.ledger.infrastructure.models import LedgerAccount
from app.shared.outbox.domain.enums import OutboxMessageStatus
from tests.unit.billing.fakes import FakeBillingUnitOfWork

pytestmark = pytest.mark.asyncio


def add_ledger_account(
    uow: FakeBillingUnitOfWork,
    *,
    tenant_id: UUID,
    purpose: LedgerAccountPurpose,
    account_type: LedgerAccountType,
    code: str,
    name: str,
) -> None:
    account = LedgerAccount(
        tenant_id=tenant_id,
        code=code,
        name=name,
        type=account_type.value,
        purpose=purpose.value,
        status=LedgerAccountStatus.ACTIVE.value,
    )
    account.id = uuid4()

    uow.fake_ledger_accounts.items.append(account)


async def test_issue_invoice_creates_pending_outbox_event() -> None:
    uow = FakeBillingUnitOfWork()

    tenant_id = uuid4()
    customer_id = uuid4()
    invoice_id = uuid4()

    invoice = Invoice(
        tenant_id=tenant_id,
        customer_id=customer_id,
        invoice_number="INV-OUTBOX-001",
        status=InvoiceStatus.DRAFT.value,
        currency="USD",
        subtotal=Decimal("100.00"),
        tax_amount=Decimal("10.00"),
        total_amount=Decimal("110.00"),
    )
    invoice.id = invoice_id

    uow.fake_invoices.items.append(invoice)

    invoice_line = InvoiceLine(
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        shipment_id=None,
        description="Shipping service",
        quantity=Decimal("1.0000"),
        unit_price=Decimal("100.00"),
        amount=Decimal("100.00"),
    )
    invoice_line.id = uuid4()

    uow.fake_invoice_lines.items.append(invoice_line)

    add_ledger_account(
        uow,
        tenant_id=tenant_id,
        purpose=LedgerAccountPurpose.ACCOUNTS_RECEIVABLE,
        account_type=LedgerAccountType.ASSET,
        code="1100",
        name="Accounts Receivable",
    )
    add_ledger_account(
        uow,
        tenant_id=tenant_id,
        purpose=LedgerAccountPurpose.REVENUE,
        account_type=LedgerAccountType.REVENUE,
        code="4000",
        name="Revenue",
    )
    add_ledger_account(
        uow,
        tenant_id=tenant_id,
        purpose=LedgerAccountPurpose.TAX_PAYABLE,
        account_type=LedgerAccountType.LIABILITY,
        code="2100",
        name="Tax Payable",
    )

    use_case = IssueInvoiceUseCase(uow)

    result = await use_case.execute(
        tenant_id=tenant_id,
        invoice_id=invoice_id,
    )

    assert result.status == InvoiceStatus.ISSUED.value
    assert result.issued_at is not None

    assert len(uow.fake_outbox_messages.items) == 1

    message = uow.fake_outbox_messages.items[0]

    assert message.tenant_id == tenant_id
    assert message.event_type == INVOICE_ISSUED_EVENT_TYPE
    assert message.status == OutboxMessageStatus.PENDING.value
    assert message.attempt_count == 0
    assert message.available_at is None
    assert message.claim_token is None
    assert message.lease_expires_at is None
    assert message.processed_at is None
    assert message.last_error is None

    assert message.payload == {
        "invoice_id": str(invoice_id),
        "customer_id": str(customer_id),
        "invoice_number": "INV-OUTBOX-001",
        "currency": "USD",
        "subtotal": "100.00",
        "tax_amount": "10.00",
        "total_amount": "110.00",
        "issued_at": result.issued_at.isoformat(),
    }

    assert uow.committed is True
    assert uow.rolled_back is False
