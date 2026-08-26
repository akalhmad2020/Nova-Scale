from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.identity.application.exceptions import (
    InvitationAlreadyPendingError,
    RoleNotFoundError,
    UserAlreadyMemberError,
)
from app.modules.identity.application.use_cases.invite_member import (
    InviteMember,
    InviteMemberCommand,
)
from app.modules.identity.domain.enums import (
    InvitationStatus,
    MembershipStatus,
)
from app.modules.identity.infrastructure.models.invitation import Invitation
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.role import Role
from app.modules.identity.infrastructure.models.user import User
from tests.unit.identity.fakes import FakeUnitOfWork


def make_role() -> Role:
    return Role(
        name=f"member-{uuid4()}",
        description="Invited member role",
    )


async def test_invite_member_creates_pending_invitation() -> None:
    uow = FakeUnitOfWork()

    role = make_role()
    uow.roles.add(role)

    tenant_id = uuid4()

    use_case = InviteMember(uow)

    invitation = await use_case.execute(
        InviteMemberCommand(
            tenant_id=tenant_id,
            email="new-member@example.com",
            role_id=role.id,
        )
    )

    assert len(uow.invitations.invitations) == 1

    stored_invitation = uow.invitations.invitations[0]

    assert stored_invitation is invitation
    assert invitation.tenant_id == tenant_id
    assert invitation.email == "new-member@example.com"
    assert invitation.role_id == role.id
    assert invitation.status is InvitationStatus.PENDING
    assert invitation.accepted_at is None


async def test_invite_member_normalizes_email() -> None:
    uow = FakeUnitOfWork()

    role = make_role()
    uow.roles.add(role)

    use_case = InviteMember(uow)

    invitation = await use_case.execute(
        InviteMemberCommand(
            tenant_id=uuid4(),
            email="  NEW-MEMBER@EXAMPLE.COM  ",
            role_id=role.id,
        )
    )

    assert invitation.email == "new-member@example.com"


async def test_invite_member_sets_expected_expiration() -> None:
    uow = FakeUnitOfWork()

    role = make_role()
    uow.roles.add(role)

    before = datetime.now(UTC)

    use_case = InviteMember(
        uow,
        invitation_ttl_days=7,
    )

    invitation = await use_case.execute(
        InviteMemberCommand(
            tenant_id=uuid4(),
            email="expires@example.com",
            role_id=role.id,
        )
    )

    after = datetime.now(UTC)

    expected_min = before + timedelta(days=7)
    expected_max = after + timedelta(days=7)

    assert expected_min <= invitation.expires_at <= expected_max


async def test_invite_member_rejects_unknown_role() -> None:
    uow = FakeUnitOfWork()

    use_case = InviteMember(uow)

    with pytest.raises(RoleNotFoundError):
        await use_case.execute(
            InviteMemberCommand(
                tenant_id=uuid4(),
                email="member@example.com",
                role_id=uuid4(),
            )
        )

    assert uow.invitations.invitations == []
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_invite_member_rejects_existing_member() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    role = make_role()
    uow.roles.add(role)

    user = User(
        email="existing@example.com",
        password_hash="hashed-password",
        first_name="Existing",
        last_name="Member",
        is_active=True,
    )

    uow.users.add(user)

    uow.memberships.add(
        Membership(
            tenant_id=tenant_id,
            user_id=user.id,
            role_id=role.id,
            status=MembershipStatus.ACTIVE,
        )
    )

    use_case = InviteMember(uow)

    with pytest.raises(UserAlreadyMemberError):
        await use_case.execute(
            InviteMemberCommand(
                tenant_id=tenant_id,
                email=user.email,
                role_id=role.id,
            )
        )

    assert uow.invitations.invitations == []
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_invite_member_rejects_existing_pending_invitation() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    role = make_role()
    uow.roles.add(role)

    existing_invitation = Invitation(
        tenant_id=tenant_id,
        role_id=role.id,
        email="pending@example.com",
        status=InvitationStatus.PENDING,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )

    uow.invitations.add(existing_invitation)

    use_case = InviteMember(uow)

    with pytest.raises(InvitationAlreadyPendingError):
        await use_case.execute(
            InviteMemberCommand(
                tenant_id=tenant_id,
                email="PENDING@EXAMPLE.COM",
                role_id=role.id,
            )
        )

    assert len(uow.invitations.invitations) == 1
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_invite_member_commits_transaction() -> None:
    uow = FakeUnitOfWork()

    role = make_role()
    uow.roles.add(role)

    use_case = InviteMember(uow)

    await use_case.execute(
        InviteMemberCommand(
            tenant_id=uuid4(),
            email="commit@example.com",
            role_id=role.id,
        )
    )

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.rolled_back is False
