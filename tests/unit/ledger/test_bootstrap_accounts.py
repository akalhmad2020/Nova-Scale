from uuid import uuid4

import pytest

from app.modules.ledger.application.use_cases.bootstrap_accounts import (
    BootstrapLedgerAccountsUseCase,
)
from app.modules.ledger.domain.enums import LedgerAccountPurpose
from tests.unit.ledger.fakes import FakeLedgerUnitOfWork

pytestmark = pytest.mark.asyncio


async def test_bootstrap_creates_system_ledger_accounts() -> None:
    tenant_id = uuid4()
    uow = FakeLedgerUnitOfWork()

    use_case = BootstrapLedgerAccountsUseCase(uow)

    accounts = await use_case.execute(tenant_id)

    assert len(accounts) == 4
    assert len(uow._accounts.items) == 4
    assert uow.committed is True

    purposes = {account.purpose for account in accounts}

    assert purposes == {
        LedgerAccountPurpose.CASH.value,
        LedgerAccountPurpose.ACCOUNTS_RECEIVABLE.value,
        LedgerAccountPurpose.TAX_PAYABLE.value,
        LedgerAccountPurpose.REVENUE.value,
    }


async def test_bootstrap_is_idempotent() -> None:
    tenant_id = uuid4()
    uow = FakeLedgerUnitOfWork()

    use_case = BootstrapLedgerAccountsUseCase(uow)

    first = await use_case.execute(tenant_id)
    second = await use_case.execute(tenant_id)

    assert len(first) == 4
    assert len(second) == 4
    assert len(uow._accounts.items) == 4
