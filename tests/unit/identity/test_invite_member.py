from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

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
from app.modules.saas.domain.enums import PlanCode, SubscriptionStatus
from app.modules.saas.infrastructure.models.subscription import TenantSubscription
from tests.unit.identity.fakes import FakeUnitOfWork


class FakeInvitationTokenService:
    def generate_token(self) -> str:
        return "test-invitation-token"

    def hash_token(
        self,
        token: str,
    ) -> str:
        return f"hashed::{token}"


def make_role() -> Role:
    return Role(
        name=f"member-{uuid4()}",
        description="Invited member role",
    )


def add_active_subscription(
    uow: FakeUnitOfWork,
    tenant_id: UUID,
) -> None:
    uow.subscriptions.add(
        TenantSubscription(
            tenant_id=tenant_id,
            plan_code=PlanCode.STARTER,
            status=SubscriptionStatus.ACTIVE,
        )
    )


def make_use_case(
    uow: FakeUnitOfWork,
    *,
    invitation_ttl_days: int = 7,
) -> InviteMember:
    return InviteMember(
        unit_of_work=uow,
        invitation_token_service=FakeInvitationTokenService(),
        invitation_ttl_days=invitation_ttl_days,
    )


async def test_invite_member_creates_pending_invitation() -> None:
    uow = FakeUnitOfWork()

    role = make_role()
    uow.roles.add(role)

    tenant_id = uuid4()
    add_active_subscription(uow, tenant_id)

    use_case = make_use_case(uow)

    result = await use_case.execute(
        InviteMemberCommand(
            tenant_id=tenant_id,
            email="new-member@example.com",
            role_id=role.id,
        )
    )

    assert len(uow.invitations.invitations) == 1

    stored_invitation = uow.invitations.invitations[0]

    assert stored_invitation.id == result.invitation_id
    assert stored_invitation.tenant_id == tenant_id
    assert stored_invitation.email == "new-member@example.com"
    assert stored_invitation.role_id == role.id
    assert stored_invitation.status is InvitationStatus.PENDING
    assert stored_invitation.accepted_at is None
    assert stored_invitation.token_hash == "hashed::test-invitation-token"

    assert result.token == "test-invitation-token"
    assert result.email == "new-member@example.com"
    assert result.tenant_id == tenant_id
    assert result.role_id == role.id


async def test_invite_member_does_not_store_raw_token() -> None:
    uow = FakeUnitOfWork()

    role = make_role()
    uow.roles.add(role)

    tenant_id = uuid4()
    add_active_subscription(uow, tenant_id)

    use_case = make_use_case(uow)

    result = await use_case.execute(
        InviteMemberCommand(
            tenant_id=tenant_id,
            email="secure@example.com",
            role_id=role.id,
        )
    )

    stored_invitation = uow.invitations.invitations[0]

    assert result.token == "test-invitation-token"
    assert stored_invitation.token_hash == "hashed::test-invitation-token"
    assert stored_invitation.token_hash != result.token


async def test_invite_member_normalizes_email() -> None:
    uow = FakeUnitOfWork()

    role = make_role()
    uow.roles.add(role)

    tenant_id = uuid4()
    add_active_subscription(uow, tenant_id)

    use_case = make_use_case(uow)

    result = await use_case.execute(
        InviteMemberCommand(
            tenant_id=tenant_id,
            email="  NEW-MEMBER@EXAMPLE.COM  ",
            role_id=role.id,
        )
    )

    assert result.email == "new-member@example.com"

    stored_invitation = uow.invitations.invitations[0]

    assert stored_invitation.email == "new-member@example.com"


async def test_invite_member_sets_expected_expiration() -> None:
    uow = FakeUnitOfWork()

    role = make_role()
    uow.roles.add(role)

    tenant_id = uuid4()
    add_active_subscription(uow, tenant_id)

    before = datetime.now(UTC)

    use_case = make_use_case(
        uow,
        invitation_ttl_days=7,
    )

    result = await use_case.execute(
        InviteMemberCommand(
            tenant_id=tenant_id,
            email="expires@example.com",
            role_id=role.id,
        )
    )

    after = datetime.now(UTC)

    expected_min = before + timedelta(days=7)
    expected_max = after + timedelta(days=7)

    assert expected_min <= result.expires_at <= expected_max


async def test_invite_member_rejects_unknown_role() -> None:
    uow = FakeUnitOfWork()

    use_case = make_use_case(uow)

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

    use_case = make_use_case(uow)

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
        token_hash="existing-token-hash",
        status=InvitationStatus.PENDING,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )

    uow.invitations.add(existing_invitation)

    use_case = make_use_case(uow)

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

    tenant_id = uuid4()
    add_active_subscription(uow, tenant_id)

    use_case = make_use_case(uow)

    await use_case.execute(
        InviteMemberCommand(
            tenant_id=tenant_id,
            email="commit@example.com",
            role_id=role.id,
        )
    )

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.rolled_back is False
