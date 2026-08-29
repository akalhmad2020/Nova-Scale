from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.ledger.application.exceptions import (
    JournalEntryNotBalancedError,
    LedgerAccountInactiveError,
    LedgerAccountNotFoundError,
)
from app.modules.ledger.application.use_cases import (
    JournalLineInput,
    PostJournalEntryUseCase,
)
from app.modules.ledger.domain.enums import LedgerAccountStatus
from app.modules.ledger.infrastructure.models import LedgerAccount
from tests.unit.ledger.fakes import FakeLedgerUnitOfWork

pytestmark = pytest.mark.asyncio


async def test_post_journal_entry_creates_balanced_entry() -> None:
    tenant_id = uuid4()
    debit_account_id = uuid4()
    credit_account_id = uuid4()

    uow = FakeLedgerUnitOfWork()

    uow._accounts.items.extend(
        [
            LedgerAccount(
                id=debit_account_id,
                tenant_id=tenant_id,
                code="1000",
                name="Cash",
                type="asset",
                purpose="cash",
                status="active",
            ),
            LedgerAccount(
                id=credit_account_id,
                tenant_id=tenant_id,
                code="1100",
                name="Accounts Receivable",
                type="asset",
                purpose="accounts_receivable",
                status="active",
            ),
        ]
    )

    use_case = PostJournalEntryUseCase(uow)

    source_id = uuid4()

    entry = await use_case.execute(
        tenant_id=tenant_id,
        source_type="payment_posted",
        source_id=source_id,
        description="Payment posted",
        posted_at=datetime.now(UTC),
        lines=[
            JournalLineInput(
                ledger_account_id=debit_account_id,
                debit=Decimal("100.00"),
                credit=Decimal("0.00"),
            ),
            JournalLineInput(
                ledger_account_id=credit_account_id,
                debit=Decimal("0.00"),
                credit=Decimal("100.00"),
            ),
        ],
    )

    assert entry.tenant_id == tenant_id
    assert entry.source_id == source_id
    assert len(uow._journal_entries.items) == 1
    assert len(uow._journal_lines.items) == 2
    assert uow.committed is True


async def test_post_journal_entry_is_idempotent() -> None:
    tenant_id = uuid4()
    debit_account_id = uuid4()
    credit_account_id = uuid4()

    uow = FakeLedgerUnitOfWork()

    uow._accounts.items.extend(
        [
            LedgerAccount(
                id=debit_account_id,
                tenant_id=tenant_id,
                code="1000",
                name="Cash",
                type="asset",
                purpose="cash",
                status="active",
            ),
            LedgerAccount(
                id=credit_account_id,
                tenant_id=tenant_id,
                code="1100",
                name="Accounts Receivable",
                type="asset",
                purpose="accounts_receivable",
                status="active",
            ),
        ]
    )

    use_case = PostJournalEntryUseCase(uow)

    source_id = uuid4()

    lines = [
        JournalLineInput(
            ledger_account_id=debit_account_id,
            debit=Decimal("100.00"),
            credit=Decimal("0.00"),
        ),
        JournalLineInput(
            ledger_account_id=credit_account_id,
            debit=Decimal("0.00"),
            credit=Decimal("100.00"),
        ),
    ]

    first = await use_case.execute(
        tenant_id=tenant_id,
        source_type="payment_posted",
        source_id=source_id,
        description="Payment posted",
        posted_at=datetime.now(UTC),
        lines=lines,
    )

    second = await use_case.execute(
        tenant_id=tenant_id,
        source_type="payment_posted",
        source_id=source_id,
        description="Payment posted",
        posted_at=datetime.now(UTC),
        lines=lines,
    )

    assert second is first
    assert len(uow._journal_entries.items) == 1
    assert len(uow._journal_lines.items) == 2


async def test_post_journal_entry_rejects_unbalanced_lines() -> None:
    uow = FakeLedgerUnitOfWork()
    use_case = PostJournalEntryUseCase(uow)

    with pytest.raises(JournalEntryNotBalancedError):
        await use_case.execute(
            tenant_id=uuid4(),
            source_type="invoice_issued",
            source_id=uuid4(),
            description="Invoice issued",
            posted_at=datetime.now(UTC),
            lines=[
                JournalLineInput(
                    ledger_account_id=uuid4(),
                    debit=Decimal("100.00"),
                    credit=Decimal("0.00"),
                ),
                JournalLineInput(
                    ledger_account_id=uuid4(),
                    debit=Decimal("0.00"),
                    credit=Decimal("90.00"),
                ),
            ],
        )


async def test_post_journal_entry_rejects_missing_account() -> None:
    uow = FakeLedgerUnitOfWork()
    use_case = PostJournalEntryUseCase(uow)

    with pytest.raises(LedgerAccountNotFoundError):
        await use_case.execute(
            tenant_id=uuid4(),
            source_type="invoice_issued",
            source_id=uuid4(),
            description="Invoice issued",
            posted_at=datetime.now(UTC),
            lines=[
                JournalLineInput(
                    ledger_account_id=uuid4(),
                    debit=Decimal("100.00"),
                    credit=Decimal("0.00"),
                ),
                JournalLineInput(
                    ledger_account_id=uuid4(),
                    debit=Decimal("0.00"),
                    credit=Decimal("100.00"),
                ),
            ],
        )


async def test_post_journal_entry_rejects_inactive_account() -> None:
    tenant_id = uuid4()
    debit_account_id = uuid4()
    credit_account_id = uuid4()

    uow = FakeLedgerUnitOfWork()

    uow._accounts.items.extend(
        [
            LedgerAccount(
                id=debit_account_id,
                tenant_id=tenant_id,
                code="1000",
                name="Cash",
                type="asset",
                purpose="cash",
                status=LedgerAccountStatus.INACTIVE.value,
            ),
            LedgerAccount(
                id=credit_account_id,
                tenant_id=tenant_id,
                code="1100",
                name="Accounts Receivable",
                type="asset",
                purpose="accounts_receivable",
                status=LedgerAccountStatus.ACTIVE.value,
            ),
        ]
    )

    use_case = PostJournalEntryUseCase(uow)

    with pytest.raises(LedgerAccountInactiveError):
        await use_case.execute(
            tenant_id=tenant_id,
            source_type="payment_posted",
            source_id=uuid4(),
            description="Payment posted",
            posted_at=datetime.now(UTC),
            lines=[
                JournalLineInput(
                    ledger_account_id=debit_account_id,
                    debit=Decimal("100.00"),
                    credit=Decimal("0.00"),
                ),
                JournalLineInput(
                    ledger_account_id=credit_account_id,
                    debit=Decimal("0.00"),
                    credit=Decimal("100.00"),
                ),
            ],
        )
