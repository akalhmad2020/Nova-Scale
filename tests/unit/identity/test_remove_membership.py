from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.identity.application.exceptions import (
    CannotRemoveLastOwnerError,
    CannotRemoveSelfError,
    MembershipNotFoundError,
    MembershipTenantMismatchError,
)
from app.modules.identity.application.use_cases.remove_membership import (
    RemoveMembership,
    RemoveMembershipCommand,
)
from app.modules.identity.domain.enums import MembershipStatus
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.role import Role
from tests.unit.identity.fakes import FakeUnitOfWork


async def test_remove_membership_soft_deletes_member() -> None:
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

    use_case = RemoveMembership(uow)

    await use_case.execute(
        RemoveMembershipCommand(
            tenant_id=tenant_id,
            membership_id=membership.id,
            actor_user_id=uuid4(),
        )
    )

    assert membership.deleted_at is not None
    assert uow.flushed is True
    assert uow.committed is True
    assert uow.rolled_back is False


async def test_remove_membership_rejects_unknown_membership() -> None:
    uow = FakeUnitOfWork()

    use_case = RemoveMembership(uow)

    with pytest.raises(MembershipNotFoundError):
        await use_case.execute(
            RemoveMembershipCommand(
                tenant_id=uuid4(),
                membership_id=uuid4(),
                actor_user_id=uuid4(),
            )
        )

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_remove_membership_rejects_other_tenant() -> None:
    uow = FakeUnitOfWork()

    membership = Membership(
        tenant_id=uuid4(),
        user_id=uuid4(),
        role_id=uuid4(),
        status=MembershipStatus.ACTIVE,
    )
    uow.memberships.add(membership)

    use_case = RemoveMembership(uow)

    with pytest.raises(MembershipTenantMismatchError):
        await use_case.execute(
            RemoveMembershipCommand(
                tenant_id=uuid4(),
                membership_id=membership.id,
                actor_user_id=uuid4(),
            )
        )

    assert membership.deleted_at is None
    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_remove_membership_rejects_self_removal() -> None:
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

    use_case = RemoveMembership(uow)

    with pytest.raises(CannotRemoveSelfError):
        await use_case.execute(
            RemoveMembershipCommand(
                tenant_id=tenant_id,
                membership_id=membership.id,
                actor_user_id=user_id,
            )
        )

    assert membership.deleted_at is None
    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_remove_membership_rejects_last_owner() -> None:
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
        role_id=owner_role.id,
        status=MembershipStatus.ACTIVE,
    )
    uow.memberships.add(membership)

    use_case = RemoveMembership(uow)

    with pytest.raises(CannotRemoveLastOwnerError):
        await use_case.execute(
            RemoveMembershipCommand(
                tenant_id=tenant_id,
                membership_id=membership.id,
                actor_user_id=uuid4(),
            )
        )

    assert membership.deleted_at is None
    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_remove_membership_allows_owner_when_another_owner_exists() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    owner_role = Role(
        name="owner",
        description="Tenant owner",
    )
    uow.roles.add(owner_role)

    target = Membership(
        tenant_id=tenant_id,
        user_id=uuid4(),
        role_id=owner_role.id,
        status=MembershipStatus.ACTIVE,
    )

    other = Membership(
        tenant_id=tenant_id,
        user_id=uuid4(),
        role_id=owner_role.id,
        status=MembershipStatus.ACTIVE,
    )

    uow.memberships.add(target)
    uow.memberships.add(other)

    use_case = RemoveMembership(uow)

    await use_case.execute(
        RemoveMembershipCommand(
            tenant_id=tenant_id,
            membership_id=target.id,
            actor_user_id=uuid4(),
        )
    )

    assert target.deleted_at is not None
    assert other.deleted_at is None

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.rolled_back is False


async def test_remove_membership_rejects_already_deleted_membership() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    membership = Membership(
        tenant_id=tenant_id,
        user_id=uuid4(),
        role_id=uuid4(),
        status=MembershipStatus.ACTIVE,
    )
    membership.deleted_at = datetime.now(UTC)

    uow.memberships.add(membership)

    use_case = RemoveMembership(uow)

    with pytest.raises(MembershipNotFoundError):
        await use_case.execute(
            RemoveMembershipCommand(
                tenant_id=tenant_id,
                membership_id=membership.id,
                actor_user_id=uuid4(),
            )
        )

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True
