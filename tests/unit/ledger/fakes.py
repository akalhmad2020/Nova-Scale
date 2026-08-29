from __future__ import annotations

from types import TracebackType
from uuid import UUID

from app.modules.ledger.application.ports import (
    JournalEntryRepository,
    JournalLineRepository,
    LedgerAccountRepository,
)
from app.modules.ledger.infrastructure.models import (
    JournalEntry,
    JournalLine,
    LedgerAccount,
)


class FakeLedgerAccountRepository:
    def __init__(self) -> None:
        self.items: list[LedgerAccount] = []

    async def add(self, account: LedgerAccount) -> None:
        self.items.append(account)

    async def get_by_id(
        self,
        tenant_id: UUID,
        account_id: UUID,
    ) -> LedgerAccount | None:
        return next(
            (
                account
                for account in self.items
                if account.tenant_id == tenant_id and account.id == account_id
            ),
            None,
        )

    async def get_by_purpose(
        self,
        tenant_id: UUID,
        purpose: str,
    ) -> LedgerAccount | None:
        return next(
            (
                account
                for account in self.items
                if account.tenant_id == tenant_id and account.purpose == purpose
            ),
            None,
        )

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[LedgerAccount]:
        return [account for account in self.items if account.tenant_id == tenant_id]


class FakeJournalEntryRepository:
    def __init__(self) -> None:
        self.items: list[JournalEntry] = []

    async def add(self, entry: JournalEntry) -> None:
        self.items.append(entry)

    async def get_by_id(
        self,
        tenant_id: UUID,
        entry_id: UUID,
    ) -> JournalEntry | None:
        return next(
            (
                entry
                for entry in self.items
                if entry.tenant_id == tenant_id and entry.id == entry_id
            ),
            None,
        )

    async def get_by_source(
        self,
        tenant_id: UUID,
        source_type: str,
        source_id: UUID,
    ) -> JournalEntry | None:
        return next(
            (
                entry
                for entry in self.items
                if entry.tenant_id == tenant_id
                and entry.source_type == source_type
                and entry.source_id == source_id
            ),
            None,
        )

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[JournalEntry]:
        return [entry for entry in self.items if entry.tenant_id == tenant_id]


class FakeJournalLineRepository:
    def __init__(self) -> None:
        self.items: list[JournalLine] = []

    async def add(self, line: JournalLine) -> None:
        self.items.append(line)

    async def list_by_entry(
        self,
        tenant_id: UUID,
        journal_entry_id: UUID,
    ) -> list[JournalLine]:
        return [
            line
            for line in self.items
            if line.tenant_id == tenant_id and line.journal_entry_id == journal_entry_id
        ]


class FakeLedgerUnitOfWork:
    accounts: LedgerAccountRepository
    journal_entries: JournalEntryRepository
    journal_lines: JournalLineRepository

    def __init__(self) -> None:
        self._accounts = FakeLedgerAccountRepository()
        self._journal_entries = FakeJournalEntryRepository()
        self._journal_lines = FakeJournalLineRepository()

        self.accounts = self._accounts
        self.journal_entries = self._journal_entries
        self.journal_lines = self._journal_lines

        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> FakeLedgerUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True
