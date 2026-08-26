from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.identity.application.exceptions import (
    InvitationEmailMismatchError,
    InvitationExpiredError,
    InvitationNotFoundError,
    InvitationNotPendingError,
    UserAlreadyMemberError,
)
from app.modules.identity.application.use_cases.accept_invitation import (
    AcceptInvitation,
    AcceptInvitationCommand,
)
from app.modules.identity.domain.enums import (
    InvitationStatus,
    MembershipStatus,
)
from app.modules.identity.infrastructure.models.invitation import Invitation
from app.modules.identity.infrastructure.models.membership import Membership
from tests.unit.identity.fakes import FakeUnitOfWork


def make_pending_invitation(
    *,
    email: str = "invited@example.com",
) -> Invitation:
    return Invitation(
        tenant_id=uuid4(),
        role_id=uuid4(),
        email=email,
        status=InvitationStatus.PENDING,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )


async def test_accept_invitation_creates_active_membership() -> None:
    uow = FakeUnitOfWork()

    invitation = make_pending_invitation()
    uow.invitations.add(invitation)

    user_id = uuid4()

    use_case = AcceptInvitation(uow)

    membership = await use_case.execute(
        AcceptInvitationCommand(
            invitation_id=invitation.id,
            user_id=user_id,
            user_email=invitation.email,
        )
    )

    assert membership.user_id == user_id
    assert membership.tenant_id == invitation.tenant_id
    assert membership.role_id == invitation.role_id
    assert membership.status is MembershipStatus.ACTIVE

    assert len(uow.memberships.memberships) == 1


async def test_accept_invitation_marks_invitation_accepted() -> None:
    uow = FakeUnitOfWork()

    invitation = make_pending_invitation()
    uow.invitations.add(invitation)

    use_case = AcceptInvitation(uow)

    await use_case.execute(
        AcceptInvitationCommand(
            invitation_id=invitation.id,
            user_id=uuid4(),
            user_email=invitation.email,
        )
    )

    assert invitation.status is InvitationStatus.ACCEPTED
    assert invitation.accepted_at is not None
    assert uow.committed is True


async def test_accept_invitation_rejects_unknown_invitation() -> None:
    uow = FakeUnitOfWork()

    use_case = AcceptInvitation(uow)

    with pytest.raises(InvitationNotFoundError):
        await use_case.execute(
            AcceptInvitationCommand(
                invitation_id=uuid4(),
                user_id=uuid4(),
                user_email="unknown@example.com",
            )
        )


async def test_accept_invitation_rejects_non_pending_invitation() -> None:
    uow = FakeUnitOfWork()

    invitation = make_pending_invitation()
    invitation.status = InvitationStatus.ACCEPTED

    uow.invitations.add(invitation)

    use_case = AcceptInvitation(uow)

    with pytest.raises(InvitationNotPendingError):
        await use_case.execute(
            AcceptInvitationCommand(
                invitation_id=invitation.id,
                user_id=uuid4(),
                user_email=invitation.email,
            )
        )


async def test_accept_invitation_rejects_expired_invitation() -> None:
    uow = FakeUnitOfWork()

    invitation = Invitation(
        tenant_id=uuid4(),
        role_id=uuid4(),
        email="expired@example.com",
        status=InvitationStatus.PENDING,
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )

    uow.invitations.add(invitation)

    use_case = AcceptInvitation(uow)

    with pytest.raises(InvitationExpiredError):
        await use_case.execute(
            AcceptInvitationCommand(
                invitation_id=invitation.id,
                user_id=uuid4(),
                user_email=invitation.email,
            )
        )

    assert invitation.status is InvitationStatus.EXPIRED


async def test_accept_invitation_rejects_email_mismatch() -> None:
    uow = FakeUnitOfWork()

    invitation = make_pending_invitation(email="invited@example.com")

    uow.invitations.add(invitation)

    use_case = AcceptInvitation(uow)

    with pytest.raises(InvitationEmailMismatchError):
        await use_case.execute(
            AcceptInvitationCommand(
                invitation_id=invitation.id,
                user_id=uuid4(),
                user_email="someone-else@example.com",
            )
        )


async def test_accept_invitation_rejects_existing_membership() -> None:
    uow = FakeUnitOfWork()

    invitation = make_pending_invitation()
    uow.invitations.add(invitation)

    user_id = uuid4()

    uow.memberships.add(
        Membership(
            tenant_id=invitation.tenant_id,
            user_id=user_id,
            role_id=invitation.role_id,
            status=MembershipStatus.ACTIVE,
        )
    )

    use_case = AcceptInvitation(uow)

    with pytest.raises(UserAlreadyMemberError):
        await use_case.execute(
            AcceptInvitationCommand(
                invitation_id=invitation.id,
                user_id=user_id,
                user_email=invitation.email,
            )
        )


async def test_accept_invitation_commits_transaction() -> None:
    uow = FakeUnitOfWork()

    invitation = make_pending_invitation()
    uow.invitations.add(invitation)

    use_case = AcceptInvitation(uow)

    await use_case.execute(
        AcceptInvitationCommand(
            invitation_id=invitation.id,
            user_id=uuid4(),
            user_email=invitation.email,
        )
    )

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.rolled_back is False
