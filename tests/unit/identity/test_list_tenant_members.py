from uuid import uuid4

from app.modules.identity.application.use_cases.list_tenant_members import (
    ListTenantMembers,
)
from app.modules.identity.domain.enums import MembershipStatus
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.user import User
from tests.unit.identity.fakes import FakeUnitOfWork


def make_user(
    *,
    email: str,
) -> User:
    return User(
        email=email,
        password_hash="hashed-password",
        first_name="Test",
        last_name="Member",
        is_active=True,
    )


async def test_list_tenant_members_returns_active_members() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()
    role_id = uuid4()

    user = make_user(
        email="member@example.com",
    )

    uow.users.add(user)

    membership = Membership(
        tenant_id=tenant_id,
        user_id=user.id,
        role_id=role_id,
        status=MembershipStatus.ACTIVE,
    )

    uow.memberships.add(membership)

    use_case = ListTenantMembers(uow)

    result = await use_case.execute(tenant_id)

    assert len(result) == 1

    member = result[0]

    assert member.user is user
    assert member.membership is membership


async def test_list_tenant_members_returns_multiple_members() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    first_user = make_user(
        email="first@example.com",
    )
    second_user = make_user(
        email="second@example.com",
    )

    uow.users.add(first_user)
    uow.users.add(second_user)

    uow.memberships.add(
        Membership(
            tenant_id=tenant_id,
            user_id=first_user.id,
            role_id=uuid4(),
            status=MembershipStatus.ACTIVE,
        )
    )

    uow.memberships.add(
        Membership(
            tenant_id=tenant_id,
            user_id=second_user.id,
            role_id=uuid4(),
            status=MembershipStatus.ACTIVE,
        )
    )

    use_case = ListTenantMembers(uow)

    result = await use_case.execute(tenant_id)

    assert len(result) == 2

    user_ids = {member.user.id for member in result}

    assert user_ids == {
        first_user.id,
        second_user.id,
    }


async def test_list_tenant_members_ignores_suspended_membership() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    user = make_user(
        email="suspended@example.com",
    )

    uow.users.add(user)

    uow.memberships.add(
        Membership(
            tenant_id=tenant_id,
            user_id=user.id,
            role_id=uuid4(),
            status=MembershipStatus.SUSPENDED,
        )
    )

    use_case = ListTenantMembers(uow)

    result = await use_case.execute(tenant_id)

    assert result == []


async def test_list_tenant_members_ignores_missing_user() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    uow.memberships.add(
        Membership(
            tenant_id=tenant_id,
            user_id=uuid4(),
            role_id=uuid4(),
            status=MembershipStatus.ACTIVE,
        )
    )

    use_case = ListTenantMembers(uow)

    result = await use_case.execute(tenant_id)

    assert result == []


async def test_list_tenant_members_returns_empty_list() -> None:
    uow = FakeUnitOfWork()

    use_case = ListTenantMembers(uow)

    result = await use_case.execute(uuid4())

    assert result == []
