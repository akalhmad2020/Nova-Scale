from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.modules.ledger.application.ports import LedgerUnitOfWork
from app.modules.ledger.application.services import (
    JournalLineInput,
    JournalPostingService,
)
from app.modules.ledger.infrastructure.models import JournalEntry


class PostJournalEntryUseCase:
    def __init__(
        self,
        uow: LedgerUnitOfWork,
    ) -> None:
        self._uow = uow

    async def execute(
        self,
        *,
        tenant_id: UUID,
        source_type: str,
        source_id: UUID,
        description: str,
        posted_at: datetime,
        lines: list[JournalLineInput],
    ) -> JournalEntry:
        async with self._uow:
            service = JournalPostingService(
                accounts=self._uow.accounts,
                journal_entries=self._uow.journal_entries,
                journal_lines=self._uow.journal_lines,
            )

            entry = await service.post(
                tenant_id=tenant_id,
                source_type=source_type,
                source_id=source_id,
                description=description,
                posted_at=posted_at,
                lines=lines,
            )

            await self._uow.commit()

            return entry
