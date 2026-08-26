from datetime import UTC, datetime
from uuid import uuid4

from app.modules.identity.application.use_cases.list_user_tenants import (
    ListUserTenants,
)
from app.modules.identity.domain.enums import (
    MembershipStatus,
    TenantStatus,
)
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.role import Role
from app.modules.identity.infrastructure.models.tenant import Tenant
from tests.unit.identity.fakes import FakeUnitOfWork


def make_tenant(
    *,
    name: str,
    slug: str,
    status: TenantStatus = TenantStatus.ACTIVE,
) -> Tenant:
    return Tenant(
        name=name,
        slug=slug,
        status=status,
    )


async def test_list_user_tenants_returns_active_memberships() -> None:
    uow = FakeUnitOfWork()

    user_id = uuid4()

    owner_role = Role(
        name="owner",
        description="Tenant owner",
    )
    uow.roles.add(owner_role)

    tenant = make_tenant(
        name="Acme Logistics",
        slug="acme-logistics",
    )
    uow.tenants.add(tenant)

    membership = Membership(
        tenant_id=tenant.id,
        user_id=user_id,
        role_id=owner_role.id,
        status=MembershipStatus.ACTIVE,
    )
    uow.memberships.add(membership)

    use_case = ListUserTenants(uow)

    result = await use_case.execute(user_id)

    assert len(result) == 1

    item = result[0]

    assert item.tenant is tenant
    assert item.membership_id == membership.id
    assert item.role_id == owner_role.id


async def test_list_user_tenants_returns_multiple_tenants() -> None:
    uow = FakeUnitOfWork()

    user_id = uuid4()
    role_id = uuid4()

    first_tenant = make_tenant(
        name="Acme Logistics",
        slug="acme-logistics",
    )

    second_tenant = make_tenant(
        name="Nova Shipping",
        slug="nova-shipping",
    )

    uow.tenants.add(first_tenant)
    uow.tenants.add(second_tenant)

    uow.memberships.add(
        Membership(
            tenant_id=first_tenant.id,
            user_id=user_id,
            role_id=role_id,
            status=MembershipStatus.ACTIVE,
        )
    )

    uow.memberships.add(
        Membership(
            tenant_id=second_tenant.id,
            user_id=user_id,
            role_id=role_id,
            status=MembershipStatus.ACTIVE,
        )
    )

    use_case = ListUserTenants(uow)

    result = await use_case.execute(user_id)

    assert len(result) == 2

    tenant_ids = {item.tenant.id for item in result}

    assert tenant_ids == {
        first_tenant.id,
        second_tenant.id,
    }


async def test_list_user_tenants_ignores_inactive_membership() -> None:
    uow = FakeUnitOfWork()

    user_id = uuid4()

    tenant = make_tenant(
        name="Suspended Membership Tenant",
        slug="suspended-membership",
    )
    uow.tenants.add(tenant)

    uow.memberships.add(
        Membership(
            tenant_id=tenant.id,
            user_id=user_id,
            role_id=uuid4(),
            status=MembershipStatus.SUSPENDED,
        )
    )

    use_case = ListUserTenants(uow)

    result = await use_case.execute(user_id)

    assert result == []


async def test_list_user_tenants_ignores_deleted_tenant() -> None:
    uow = FakeUnitOfWork()

    user_id = uuid4()

    tenant = make_tenant(
        name="Deleted Tenant",
        slug="deleted-tenant",
    )

    tenant.deleted_at = datetime.now(UTC)

    uow.tenants.add(tenant)

    uow.memberships.add(
        Membership(
            tenant_id=tenant.id,
            user_id=user_id,
            role_id=uuid4(),
            status=MembershipStatus.ACTIVE,
        )
    )

    use_case = ListUserTenants(uow)

    result = await use_case.execute(user_id)

    assert result == []


async def test_list_user_tenants_returns_empty_list_for_user_without_memberships() -> None:
    uow = FakeUnitOfWork()

    use_case = ListUserTenants(uow)

    result = await use_case.execute(uuid4())

    assert result == []
