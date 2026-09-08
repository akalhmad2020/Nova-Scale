from uuid import uuid4

import pytest

from app.modules.identity.application.exceptions import (
    EmailAlreadyRegisteredError,
    TenantSlugAlreadyExistsError,
)
from app.modules.identity.application.use_cases.register_company import (
    RegisterCompany,
    RegisterCompanyCommand,
)
from app.modules.identity.domain.enums import MembershipStatus, TenantStatus
from app.modules.identity.infrastructure.models.role import Role
from app.modules.identity.infrastructure.models.tenant import Tenant
from app.modules.identity.infrastructure.models.user import User
from app.modules.ledger.application.use_cases.bootstrap_accounts import (
    SYSTEM_LEDGER_ACCOUNTS,
)
from app.modules.saas.domain.enums import PlanCode, SubscriptionStatus
from tests.unit.identity.fakes import (
    FakePasswordHasher,
    FakeUnitOfWork,
)


def build_use_case() -> tuple[
    RegisterCompany,
    FakeUnitOfWork,
    Role,
]:
    uow = FakeUnitOfWork()

    owner_role = Role(
        name="owner",
        description="Tenant owner",
    )
    uow.roles.add(owner_role)

    use_case = RegisterCompany(
        unit_of_work=uow,
        password_hasher=FakePasswordHasher(),
    )

    return use_case, uow, owner_role


@pytest.mark.asyncio
async def test_register_company_creates_owner_and_tenant() -> None:
    use_case, uow, owner_role = build_use_case()

    result = await use_case.execute(
        RegisterCompanyCommand(
            email=" Owner@Example.com ",
            password="very-secure-password",
            first_name=" Ahmed ",
            last_name=" Akram ",
            company_name=" Nova Logistics ",
            company_slug=" Nova-Logistics ",
        )
    )

    assert uow.committed is True
    assert uow.rolled_back is False

    assert len(uow.users.users) == 1
    user = uow.users.users[0]

    assert user.email == "owner@example.com"
    assert user.password_hash == "hashed::very-secure-password"
    assert user.first_name == "Ahmed"
    assert user.last_name == "Akram"

    assert len(uow.tenants.tenants) == 1
    tenant = uow.tenants.tenants[0]

    assert tenant.name == "Nova Logistics"
    assert tenant.slug == "nova-logistics"
    assert tenant.status is TenantStatus.ACTIVE

    assert len(uow.memberships.memberships) == 1
    membership = uow.memberships.memberships[0]

    assert membership.user_id == user.id
    assert membership.tenant_id == tenant.id
    assert membership.role_id == owner_role.id
    assert membership.status is MembershipStatus.ACTIVE

    assert len(uow.ledger_accounts.accounts) == len(SYSTEM_LEDGER_ACCOUNTS)

    assert all(account.tenant_id == tenant.id for account in uow.ledger_accounts.accounts)

    assert len(uow.subscriptions.subscriptions) == 1
    subscription = uow.subscriptions.subscriptions[0]
    assert subscription.tenant_id == tenant.id
    assert subscription.plan_code is PlanCode.STARTER
    assert subscription.status is SubscriptionStatus.ACTIVE

    assert result.user_id == user.id
    assert result.tenant_id == tenant.id
    assert result.membership_id == membership.id
    assert result.email == "owner@example.com"
    assert result.company_name == "Nova Logistics"
    assert result.company_slug == "nova-logistics"


@pytest.mark.asyncio
async def test_register_company_rejects_duplicate_email() -> None:
    use_case, uow, _ = build_use_case()

    existing_user = User(
        email="owner@example.com",
        password_hash="existing-hash",
        first_name="Existing",
        last_name="Owner",
    )
    existing_user.id = uuid4()
    uow.users.add(existing_user)

    with pytest.raises(EmailAlreadyRegisteredError):
        await use_case.execute(
            RegisterCompanyCommand(
                email=" OWNER@example.com ",
                password="very-secure-password",
                first_name="Ahmed",
                last_name="Akram",
                company_name="Nova Logistics",
                company_slug="nova-logistics",
            )
        )

    assert uow.committed is False
    assert len(uow.tenants.tenants) == 0
    assert len(uow.memberships.memberships) == 0
    assert len(uow.ledger_accounts.accounts) == 0
    assert len(uow.subscriptions.subscriptions) == 0


@pytest.mark.asyncio
async def test_register_company_rejects_duplicate_tenant_slug() -> None:
    use_case, uow, _ = build_use_case()

    existing_tenant = Tenant(
        name="Existing Company",
        slug="nova-logistics",
        status=TenantStatus.ACTIVE,
    )
    existing_tenant.id = uuid4()
    uow.tenants.add(existing_tenant)

    with pytest.raises(TenantSlugAlreadyExistsError):
        await use_case.execute(
            RegisterCompanyCommand(
                email="owner@example.com",
                password="very-secure-password",
                first_name="Ahmed",
                last_name="Akram",
                company_name="Nova Logistics",
                company_slug=" Nova-Logistics ",
            )
        )

    assert uow.committed is False
    assert len(uow.users.users) == 0
    assert len(uow.memberships.memberships) == 0
    assert len(uow.ledger_accounts.accounts) == 0
    assert len(uow.subscriptions.subscriptions) == 0


@pytest.mark.asyncio
async def test_register_company_requires_owner_role() -> None:
    uow = FakeUnitOfWork()

    use_case = RegisterCompany(
        unit_of_work=uow,
        password_hasher=FakePasswordHasher(),
    )

    with pytest.raises(
        RuntimeError,
        match="Owner role is not configured",
    ):
        await use_case.execute(
            RegisterCompanyCommand(
                email="owner@example.com",
                password="very-secure-password",
                first_name="Ahmed",
                last_name="Akram",
                company_name="Nova Logistics",
                company_slug="nova-logistics",
            )
        )

    assert uow.committed is False
