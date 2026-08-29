from __future__ import annotations

from types import TracebackType
from typing import Protocol

from app.modules.ledger.application.ports.repositories import (
    JournalEntryRepository,
    JournalLineRepository,
    LedgerAccountRepository,
)


class LedgerUnitOfWork(Protocol):
    accounts: LedgerAccountRepository
    journal_entries: JournalEntryRepository
    journal_lines: JournalLineRepository

    async def __aenter__(self) -> LedgerUnitOfWork: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
