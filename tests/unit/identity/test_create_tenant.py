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
from tests.unit.identity.fakes import FakeUnitOfWork


def make_owner_role() -> Role:
    return Role(
        name="owner",
        description="Tenant owner",
    )


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
