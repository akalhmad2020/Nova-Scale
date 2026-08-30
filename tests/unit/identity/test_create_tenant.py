from uuid import uuid4

import pytest

from app.modules.identity.application.exceptions import (
    TenantSlugAlreadyExistsError,
)
from app.modules.identity.application.use_cases.create_tenant import (
    CreateTenant,
    CreateTenantCommand,
)
from app.modules.identity.domain.enums import (
    MembershipStatus,
    TenantStatus,
)
from app.modules.identity.infrastructure.models.role import Role
from app.modules.identity.infrastructure.models.tenant import Tenant
from app.modules.ledger.domain.enums import (
    LedgerAccountPurpose,
    LedgerAccountStatus,
    LedgerAccountType,
)
from app.modules.ledger.infrastructure.models import LedgerAccount
from tests.unit.identity.fakes import (
    FakeLedgerAccountRepository,
    FakeUnitOfWork,
)


def make_owner_role() -> Role:
    return Role(
        name="owner",
        description="Tenant owner",
    )


class FailingLedgerAccountRepository(
    FakeLedgerAccountRepository,
):
    async def add(
        self,
        account: LedgerAccount,
    ) -> None:
        if account.purpose == LedgerAccountPurpose.TAX_PAYABLE.value:
            raise RuntimeError("Forced ledger provisioning failure")

        await super().add(account)


async def test_create_tenant_creates_tenant() -> None:
    uow = FakeUnitOfWork()

    owner_role = make_owner_role()
    uow.roles.add(owner_role)

    user_id = uuid4()

    use_case = CreateTenant(uow)

    result = await use_case.execute(
        CreateTenantCommand(
            user_id=user_id,
            name="Acme Logistics",
            slug="acme-logistics",
        )
    )

    assert len(uow.tenants.tenants) == 1

    tenant = uow.tenants.tenants[0]

    assert tenant.name == "Acme Logistics"
    assert tenant.slug == "acme-logistics"
    assert tenant.status is TenantStatus.ACTIVE

    assert result.tenant_id == tenant.id


async def test_create_tenant_creates_owner_membership() -> None:
    uow = FakeUnitOfWork()

    owner_role = make_owner_role()
    uow.roles.add(owner_role)

    user_id = uuid4()

    use_case = CreateTenant(uow)

    result = await use_case.execute(
        CreateTenantCommand(
            user_id=user_id,
            name="Acme Logistics",
            slug="acme-logistics",
        )
    )

    assert len(uow.memberships.memberships) == 1

    membership = uow.memberships.memberships[0]

    assert membership.user_id == user_id
    assert membership.tenant_id == result.tenant_id
    assert membership.role_id == owner_role.id
    assert membership.status is MembershipStatus.ACTIVE

    assert result.membership_id == membership.id


async def test_create_tenant_creates_system_ledger_accounts() -> None:
    uow = FakeUnitOfWork()
    uow.roles.add(make_owner_role())

    use_case = CreateTenant(uow)

    result = await use_case.execute(
        CreateTenantCommand(
            user_id=uuid4(),
            name="Acme Logistics",
            slug="acme-logistics",
        )
    )

    accounts = await uow.ledger_accounts.list_by_tenant(
        result.tenant_id,
    )

    assert len(accounts) == 4

    by_purpose = {account.purpose: account for account in accounts}

    cash = by_purpose[LedgerAccountPurpose.CASH.value]
    assert cash.code == "1000"
    assert cash.name == "Cash"
    assert cash.type == LedgerAccountType.ASSET.value
    assert cash.status == LedgerAccountStatus.ACTIVE.value

    accounts_receivable = by_purpose[LedgerAccountPurpose.ACCOUNTS_RECEIVABLE.value]
    assert accounts_receivable.code == "1100"
    assert accounts_receivable.name == "Accounts Receivable"
    assert accounts_receivable.type == LedgerAccountType.ASSET.value
    assert accounts_receivable.status == LedgerAccountStatus.ACTIVE.value

    tax_payable = by_purpose[LedgerAccountPurpose.TAX_PAYABLE.value]
    assert tax_payable.code == "2100"
    assert tax_payable.name == "Tax Payable"
    assert tax_payable.type == LedgerAccountType.LIABILITY.value
    assert tax_payable.status == LedgerAccountStatus.ACTIVE.value

    revenue = by_purpose[LedgerAccountPurpose.REVENUE.value]
    assert revenue.code == "4000"
    assert revenue.name == "Revenue"
    assert revenue.type == LedgerAccountType.REVENUE.value
    assert revenue.status == LedgerAccountStatus.ACTIVE.value

    assert {account.tenant_id for account in accounts} == {result.tenant_id}


async def test_create_tenant_rolls_back_when_ledger_provisioning_fails() -> None:
    uow = FakeUnitOfWork()
    uow.roles.add(make_owner_role())

    uow._ledger_accounts = FailingLedgerAccountRepository()

    use_case = CreateTenant(uow)

    with pytest.raises(
        RuntimeError,
        match="Forced ledger provisioning failure",
    ):
        await use_case.execute(
            CreateTenantCommand(
                user_id=uuid4(),
                name="Atomic Logistics",
                slug="atomic-logistics",
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_create_tenant_normalizes_name_and_slug() -> None:
    uow = FakeUnitOfWork()

    uow.roles.add(make_owner_role())

    use_case = CreateTenant(uow)

    result = await use_case.execute(
        CreateTenantCommand(
            user_id=uuid4(),
            name="  Acme Logistics  ",
            slug="  ACME-LOGISTICS  ",
        )
    )

    assert result.name == "Acme Logistics"
    assert result.slug == "acme-logistics"


async def test_create_tenant_rejects_duplicate_slug() -> None:
    uow = FakeUnitOfWork()

    existing_tenant = Tenant(
        name="Existing Tenant",
        slug="acme-logistics",
        status=TenantStatus.ACTIVE,
    )

    uow.tenants.add(existing_tenant)
    uow.roles.add(make_owner_role())

    use_case = CreateTenant(uow)

    with pytest.raises(TenantSlugAlreadyExistsError):
        await use_case.execute(
            CreateTenantCommand(
                user_id=uuid4(),
                name="Another Tenant",
                slug="ACME-LOGISTICS",
            )
        )

    assert len(uow.tenants.tenants) == 1
    assert len(uow.memberships.memberships) == 0
    assert len(uow.ledger_accounts.accounts) == 0
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_create_tenant_requires_owner_role() -> None:
    uow = FakeUnitOfWork()

    use_case = CreateTenant(uow)

    with pytest.raises(
        RuntimeError,
        match="Owner role is not configured",
    ):
        await use_case.execute(
            CreateTenantCommand(
                user_id=uuid4(),
                name="Acme Logistics",
                slug="acme-logistics",
            )
        )

    assert len(uow.tenants.tenants) == 0
    assert len(uow.memberships.memberships) == 0
    assert len(uow.ledger_accounts.accounts) == 0
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_create_tenant_commits_transaction() -> None:
    uow = FakeUnitOfWork()

    uow.roles.add(make_owner_role())

    use_case = CreateTenant(uow)

    await use_case.execute(
        CreateTenantCommand(
            user_id=uuid4(),
            name="Acme Logistics",
            slug="acme-logistics",
        )
    )

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.rolled_back is False
