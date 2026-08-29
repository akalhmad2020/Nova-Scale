from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.modules.ledger.infrastructure.models import (
    JournalEntry,
    JournalLine,
    LedgerAccount,
)


class LedgerAccountRepository(Protocol):
    async def add(self, account: LedgerAccount) -> None: ...

    async def get_by_id(
        self,
        tenant_id: UUID,
        account_id: UUID,
    ) -> LedgerAccount | None: ...

    async def get_by_purpose(
        self,
        tenant_id: UUID,
        purpose: str,
    ) -> LedgerAccount | None: ...

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> Sequence[LedgerAccount]: ...


class JournalEntryRepository(Protocol):
    async def add(self, entry: JournalEntry) -> None: ...

    async def get_by_id(
        self,
        tenant_id: UUID,
        entry_id: UUID,
    ) -> JournalEntry | None: ...

    async def get_by_source(
        self,
        tenant_id: UUID,
        source_type: str,
        source_id: UUID,
    ) -> JournalEntry | None: ...

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> Sequence[JournalEntry]: ...


class JournalLineRepository(Protocol):
    async def add(self, line: JournalLine) -> None: ...

    async def list_by_entry(
        self,
        tenant_id: UUID,
        journal_entry_id: UUID,
    ) -> Sequence[JournalLine]: ...
