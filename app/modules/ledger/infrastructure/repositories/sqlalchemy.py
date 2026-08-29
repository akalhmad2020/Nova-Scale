from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ledger.infrastructure.models import (
    JournalEntry,
    JournalLine,
    LedgerAccount,
)


class SQLAlchemyLedgerAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, account: LedgerAccount) -> None:
        self._session.add(account)
        await self._session.flush()

    async def get_by_id(
        self,
        tenant_id: UUID,
        account_id: UUID,
    ) -> LedgerAccount | None:
        result = await self._session.execute(
            select(LedgerAccount).where(
                LedgerAccount.tenant_id == tenant_id,
                LedgerAccount.id == account_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_purpose(
        self,
        tenant_id: UUID,
        purpose: str,
    ) -> LedgerAccount | None:
        result = await self._session.execute(
            select(LedgerAccount).where(
                LedgerAccount.tenant_id == tenant_id,
                LedgerAccount.purpose == purpose,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> Sequence[LedgerAccount]:
        result = await self._session.execute(
            select(LedgerAccount)
            .where(LedgerAccount.tenant_id == tenant_id)
            .order_by(LedgerAccount.code.asc())
        )
        return result.scalars().all()


class SQLAlchemyJournalEntryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entry: JournalEntry) -> None:
        self._session.add(entry)
        await self._session.flush()

    async def get_by_id(
        self,
        tenant_id: UUID,
        entry_id: UUID,
    ) -> JournalEntry | None:
        result = await self._session.execute(
            select(JournalEntry).where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.id == entry_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_source(
        self,
        tenant_id: UUID,
        source_type: str,
        source_id: UUID,
    ) -> JournalEntry | None:
        result = await self._session.execute(
            select(JournalEntry).where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.source_type == source_type,
                JournalEntry.source_id == source_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> Sequence[JournalEntry]:
        result = await self._session.execute(
            select(JournalEntry)
            .where(JournalEntry.tenant_id == tenant_id)
            .order_by(
                JournalEntry.posted_at.desc(),
                JournalEntry.id.desc(),
            )
        )
        return result.scalars().all()


class SQLAlchemyJournalLineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, line: JournalLine) -> None:
        self._session.add(line)
        await self._session.flush()

    async def list_by_entry(
        self,
        tenant_id: UUID,
        journal_entry_id: UUID,
    ) -> Sequence[JournalLine]:
        result = await self._session.execute(
            select(JournalLine)
            .where(
                JournalLine.tenant_id == tenant_id,
                JournalLine.journal_entry_id == journal_entry_id,
            )
            .order_by(JournalLine.created_at.asc(), JournalLine.id.asc())
        )
        return result.scalars().all()
