from uuid import uuid4

import pytest

from app.modules.identity.application.exceptions import (
    MembershipNotFoundError,
    MembershipTenantMismatchError,
    RoleNotFoundError,
)
from app.modules.identity.application.use_cases.change_member_role import (
    ChangeMemberRole,
    ChangeMemberRoleCommand,
)
from app.modules.identity.domain.enums import MembershipStatus
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.role import Role
from tests.unit.identity.fakes import FakeUnitOfWork


async def test_change_member_role_updates_role() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    old_role = Role(
        name="old-role",
        description=None,
    )

    new_role = Role(
        name="new-role",
        description=None,
    )

    uow.roles.add(old_role)
    uow.roles.add(new_role)

    membership = Membership(
        tenant_id=tenant_id,
        user_id=uuid4(),
        role_id=old_role.id,
        status=MembershipStatus.ACTIVE,
    )

    uow.memberships.add(membership)

    use_case = ChangeMemberRole(uow)

    result = await use_case.execute(
        ChangeMemberRoleCommand(
            tenant_id=tenant_id,
            membership_id=membership.id,
            role_id=new_role.id,
        )
    )

    assert result is membership
    assert membership.role_id == new_role.id
    assert uow.flushed is True
    assert uow.committed is True
    assert uow.rolled_back is False


async def test_change_member_role_rejects_unknown_membership() -> None:
    uow = FakeUnitOfWork()

    role = Role(
        name="member",
        description=None,
    )

    uow.roles.add(role)

    use_case = ChangeMemberRole(uow)

    with pytest.raises(MembershipNotFoundError):
        await use_case.execute(
            ChangeMemberRoleCommand(
                tenant_id=uuid4(),
                membership_id=uuid4(),
                role_id=role.id,
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_change_member_role_rejects_membership_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    membership = Membership(
        tenant_id=uuid4(),
        user_id=uuid4(),
        role_id=uuid4(),
        status=MembershipStatus.ACTIVE,
    )

    uow.memberships.add(membership)

    role = Role(
        name="member",
        description=None,
    )

    uow.roles.add(role)

    use_case = ChangeMemberRole(uow)

    with pytest.raises(MembershipTenantMismatchError):
        await use_case.execute(
            ChangeMemberRoleCommand(
                tenant_id=uuid4(),
                membership_id=membership.id,
                role_id=role.id,
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_change_member_role_rejects_unknown_role() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    membership = Membership(
        tenant_id=tenant_id,
        user_id=uuid4(),
        role_id=uuid4(),
        status=MembershipStatus.ACTIVE,
    )

    uow.memberships.add(membership)

    use_case = ChangeMemberRole(uow)

    original_role_id = membership.role_id

    with pytest.raises(RoleNotFoundError):
        await use_case.execute(
            ChangeMemberRoleCommand(
                tenant_id=tenant_id,
                membership_id=membership.id,
                role_id=uuid4(),
            )
        )

    assert membership.role_id == original_role_id
    assert uow.committed is False
    assert uow.rolled_back is True
