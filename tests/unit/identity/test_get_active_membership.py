from uuid import UUID, uuid4

import pytest

from app.modules.identity.application.exceptions import (
    InactiveMembershipError,
    InactiveTenantError,
    MembershipNotFoundError,
    TenantNotFoundError,
)
from app.modules.identity.application.use_cases.get_active_membership import (
    GetActiveMembership,
    GetActiveMembershipQuery,
)
from app.modules.identity.domain.enums import (
    MembershipStatus,
    TenantStatus,
)
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.tenant import Tenant
from tests.unit.identity.fakes import FakeUnitOfWork


def make_tenant(
    *,
    status: TenantStatus = TenantStatus.ACTIVE,
) -> Tenant:
    return Tenant(
        name="Acme Logistics",
        slug=f"acme-{uuid4()}",
        status=status,
    )


def make_membership(
    *,
    tenant_id: UUID,
    user_id: UUID,
    status: MembershipStatus = MembershipStatus.ACTIVE,
) -> Membership:
    return Membership(
        tenant_id=tenant_id,
        user_id=user_id,
        role_id=uuid4(),
        status=status,
    )


async def test_returns_active_membership() -> None:
    uow = FakeUnitOfWork()

    user_id = uuid4()
    tenant = make_tenant()

    uow.tenants.add(tenant)

    membership = make_membership(
        tenant_id=tenant.id,
        user_id=user_id,
    )
    uow.memberships.add(membership)

    use_case = GetActiveMembership(uow)

    result = await use_case.execute(
        GetActiveMembershipQuery(
            user_id=user_id,
            tenant_id=tenant.id,
        )
    )

    assert result is membership


async def test_rejects_unknown_tenant() -> None:
    uow = FakeUnitOfWork()

    use_case = GetActiveMembership(uow)

    with pytest.raises(TenantNotFoundError):
        await use_case.execute(
            GetActiveMembershipQuery(
                user_id=uuid4(),
                tenant_id=uuid4(),
            )
        )


async def test_rejects_inactive_tenant() -> None:
    uow = FakeUnitOfWork()

    tenant = make_tenant(
        status=TenantStatus.SUSPENDED,
    )
    uow.tenants.add(tenant)

    use_case = GetActiveMembership(uow)

    with pytest.raises(InactiveTenantError):
        await use_case.execute(
            GetActiveMembershipQuery(
                user_id=uuid4(),
                tenant_id=tenant.id,
            )
        )


async def test_rejects_missing_membership() -> None:
    uow = FakeUnitOfWork()

    tenant = make_tenant()
    uow.tenants.add(tenant)

    use_case = GetActiveMembership(uow)

    with pytest.raises(MembershipNotFoundError):
        await use_case.execute(
            GetActiveMembershipQuery(
                user_id=uuid4(),
                tenant_id=tenant.id,
            )
        )


async def test_rejects_inactive_membership() -> None:
    uow = FakeUnitOfWork()

    user_id = uuid4()
    tenant = make_tenant()

    uow.tenants.add(tenant)

    membership = make_membership(
        tenant_id=tenant.id,
        user_id=user_id,
        status=MembershipStatus.SUSPENDED,
    )
    uow.memberships.add(membership)

    use_case = GetActiveMembership(uow)

    with pytest.raises(InactiveMembershipError):
        await use_case.execute(
            GetActiveMembershipQuery(
                user_id=user_id,
                tenant_id=tenant.id,
            )
        )
