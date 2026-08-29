from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.ledger.application.ports import LedgerUnitOfWork
from app.modules.ledger.domain.enums import (
    LedgerAccountPurpose,
    LedgerAccountStatus,
    LedgerAccountType,
)
from app.modules.ledger.infrastructure.models import LedgerAccount


@dataclass(frozen=True, slots=True)
class SystemLedgerAccountDefinition:
    code: str
    name: str
    type: LedgerAccountType
    purpose: LedgerAccountPurpose


SYSTEM_LEDGER_ACCOUNTS: tuple[SystemLedgerAccountDefinition, ...] = (
    SystemLedgerAccountDefinition(
        code="1000",
        name="Cash",
        type=LedgerAccountType.ASSET,
        purpose=LedgerAccountPurpose.CASH,
    ),
    SystemLedgerAccountDefinition(
        code="1100",
        name="Accounts Receivable",
        type=LedgerAccountType.ASSET,
        purpose=LedgerAccountPurpose.ACCOUNTS_RECEIVABLE,
    ),
    SystemLedgerAccountDefinition(
        code="2100",
        name="Tax Payable",
        type=LedgerAccountType.LIABILITY,
        purpose=LedgerAccountPurpose.TAX_PAYABLE,
    ),
    SystemLedgerAccountDefinition(
        code="4000",
        name="Revenue",
        type=LedgerAccountType.REVENUE,
        purpose=LedgerAccountPurpose.REVENUE,
    ),
)


class BootstrapLedgerAccountsUseCase:
    def __init__(self, uow: LedgerUnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        tenant_id: UUID,
    ) -> list[LedgerAccount]:
        accounts: list[LedgerAccount] = []

        async with self._uow:
            for definition in SYSTEM_LEDGER_ACCOUNTS:
                existing = await self._uow.accounts.get_by_purpose(
                    tenant_id,
                    definition.purpose.value,
                )

                if existing is not None:
                    accounts.append(existing)
                    continue

                account = LedgerAccount(
                    tenant_id=tenant_id,
                    code=definition.code,
                    name=definition.name,
                    type=definition.type.value,
                    purpose=definition.purpose.value,
                    status=LedgerAccountStatus.ACTIVE.value,
                )

                await self._uow.accounts.add(account)
                accounts.append(account)

            await self._uow.commit()

        return accounts
