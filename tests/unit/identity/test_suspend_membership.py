from uuid import uuid4

import pytest

from app.modules.identity.application.exceptions import (
    CannotSuspendLastOwnerError,
    CannotSuspendSelfError,
    MembershipNotFoundError,
    MembershipTenantMismatchError,
)
from app.modules.identity.application.use_cases.suspend_membership import (
    SuspendMembership,
    SuspendMembershipCommand,
)
from app.modules.identity.domain.enums import MembershipStatus
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.role import Role
from tests.unit.identity.fakes import FakeUnitOfWork


async def test_suspend_membership_suspends_active_membership() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    owner_role = Role(
        name="owner",
        description="Tenant owner",
    )

    uow.roles.add(owner_role)

    membership = Membership(
        tenant_id=tenant_id,
        user_id=uuid4(),
        role_id=uuid4(),
        status=MembershipStatus.ACTIVE,
    )

    uow.memberships.add(membership)

    use_case = SuspendMembership(uow)

    result = await use_case.execute(
        SuspendMembershipCommand(
            tenant_id=tenant_id,
            membership_id=membership.id,
            actor_user_id=uuid4(),
        )
    )

    assert result is membership
    assert membership.status is MembershipStatus.SUSPENDED

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.rolled_back is False


async def test_suspend_membership_rejects_unknown_membership() -> None:
    uow = FakeUnitOfWork()

    use_case = SuspendMembership(uow)

    with pytest.raises(MembershipNotFoundError):
        await use_case.execute(
            SuspendMembershipCommand(
                tenant_id=uuid4(),
                membership_id=uuid4(),
                actor_user_id=uuid4(),
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_suspend_membership_rejects_membership_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    membership = Membership(
        tenant_id=uuid4(),
        user_id=uuid4(),
        role_id=uuid4(),
        status=MembershipStatus.ACTIVE,
    )

    uow.memberships.add(membership)

    use_case = SuspendMembership(uow)

    with pytest.raises(MembershipTenantMismatchError):
        await use_case.execute(
            SuspendMembershipCommand(
                tenant_id=uuid4(),
                membership_id=membership.id,
                actor_user_id=uuid4(),
            )
        )

    assert membership.status is MembershipStatus.ACTIVE
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_suspend_membership_is_idempotent_for_suspended_membership() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    membership = Membership(
        tenant_id=tenant_id,
        user_id=uuid4(),
        role_id=uuid4(),
        status=MembershipStatus.SUSPENDED,
    )

    uow.memberships.add(membership)

    use_case = SuspendMembership(uow)

    result = await use_case.execute(
        SuspendMembershipCommand(
            tenant_id=tenant_id,
            membership_id=membership.id,
            actor_user_id=uuid4(),
        )
    )

    assert result is membership
    assert membership.status is MembershipStatus.SUSPENDED

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is False


async def test_suspend_membership_rejects_self_suspension() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()
    user_id = uuid4()

    membership = Membership(
        tenant_id=tenant_id,
        user_id=user_id,
        role_id=uuid4(),
        status=MembershipStatus.ACTIVE,
    )

    uow.memberships.add(membership)

    use_case = SuspendMembership(uow)

    with pytest.raises(CannotSuspendSelfError):
        await use_case.execute(
            SuspendMembershipCommand(
                tenant_id=tenant_id,
                membership_id=membership.id,
                actor_user_id=user_id,
            )
        )

    assert membership.status is MembershipStatus.ACTIVE
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_suspend_membership_rejects_last_active_owner() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    owner_role = Role(
        name="owner",
        description="Tenant owner",
    )

    uow.roles.add(owner_role)

    owner_membership = Membership(
        tenant_id=tenant_id,
        user_id=uuid4(),
        role_id=owner_role.id,
        status=MembershipStatus.ACTIVE,
    )

    uow.memberships.add(owner_membership)

    use_case = SuspendMembership(uow)

    with pytest.raises(CannotSuspendLastOwnerError):
        await use_case.execute(
            SuspendMembershipCommand(
                tenant_id=tenant_id,
                membership_id=owner_membership.id,
                actor_user_id=uuid4(),
            )
        )

    assert owner_membership.status is MembershipStatus.ACTIVE
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_suspend_membership_allows_owner_when_another_active_owner_exists() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    owner_role = Role(
        name="owner",
        description="Tenant owner",
    )

    uow.roles.add(owner_role)

    target_owner = Membership(
        tenant_id=tenant_id,
        user_id=uuid4(),
        role_id=owner_role.id,
        status=MembershipStatus.ACTIVE,
    )

    other_owner = Membership(
        tenant_id=tenant_id,
        user_id=uuid4(),
        role_id=owner_role.id,
        status=MembershipStatus.ACTIVE,
    )

    uow.memberships.add(target_owner)
    uow.memberships.add(other_owner)

    use_case = SuspendMembership(uow)

    result = await use_case.execute(
        SuspendMembershipCommand(
            tenant_id=tenant_id,
            membership_id=target_owner.id,
            actor_user_id=uuid4(),
        )
    )

    assert result is target_owner
    assert target_owner.status is MembershipStatus.SUSPENDED
    assert other_owner.status is MembershipStatus.ACTIVE

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.rolled_back is False
