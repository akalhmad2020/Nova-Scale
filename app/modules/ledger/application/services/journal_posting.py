from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.modules.ledger.application.exceptions import (
    LedgerAccountInactiveError,
    LedgerAccountNotFoundError,
)
from app.modules.ledger.application.ports.repositories import (
    JournalEntryRepository,
    JournalLineRepository,
    LedgerAccountRepository,
)
from app.modules.ledger.domain.enums import LedgerAccountStatus
from app.modules.ledger.domain.rules import (
    JournalAmount,
    validate_balanced_journal,
)
from app.modules.ledger.infrastructure.models import (
    JournalEntry,
    JournalLine,
)


@dataclass(frozen=True, slots=True)
class JournalLineInput:
    ledger_account_id: UUID
    debit: Decimal
    credit: Decimal
    description: str | None = None


class JournalPostingService:
    def __init__(
        self,
        *,
        accounts: LedgerAccountRepository,
        journal_entries: JournalEntryRepository,
        journal_lines: JournalLineRepository,
    ) -> None:
        self._accounts = accounts
        self._journal_entries = journal_entries
        self._journal_lines = journal_lines

    async def post(
        self,
        *,
        tenant_id: UUID,
        source_type: str,
        source_id: UUID,
        description: str,
        posted_at: datetime,
        lines: list[JournalLineInput],
        allow_inactive_accounts: bool = False,
    ) -> JournalEntry:
        validate_balanced_journal(
            JournalAmount(
                debit=line.debit,
                credit=line.credit,
            )
            for line in lines
        )

        existing = await self._journal_entries.get_by_source(
            tenant_id,
            source_type,
            source_id,
        )

        if existing is not None:
            return existing

        for line in lines:
            account = await self._accounts.get_by_id(
                tenant_id,
                line.ledger_account_id,
            )

            if account is None:
                raise LedgerAccountNotFoundError

            if account.status != LedgerAccountStatus.ACTIVE.value and not allow_inactive_accounts:
                raise LedgerAccountInactiveError

        entry = JournalEntry(
            tenant_id=tenant_id,
            source_type=source_type,
            source_id=source_id,
            description=description.strip(),
            posted_at=posted_at,
        )

        await self._journal_entries.add(entry)

        for line in lines:
            journal_line = JournalLine(
                tenant_id=tenant_id,
                journal_entry_id=entry.id,
                ledger_account_id=line.ledger_account_id,
                debit=line.debit,
                credit=line.credit,
                description=(
                    line.description.strip()
                    if line.description is not None and line.description.strip()
                    else None
                ),
            )

            await self._journal_lines.add(journal_line)

        return entry
