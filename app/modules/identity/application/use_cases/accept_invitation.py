from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.modules.identity.application.exceptions import (
    InvitationEmailMismatchError,
    InvitationExpiredError,
    InvitationNotFoundError,
    InvitationNotPendingError,
    UserAlreadyMemberError,
)
from app.modules.identity.application.ports.unit_of_work import UnitOfWork
from app.modules.identity.domain.enums import (
    InvitationStatus,
    MembershipStatus,
)
from app.modules.identity.infrastructure.models.membership import Membership


@dataclass(frozen=True, slots=True)
class AcceptInvitationCommand:
    invitation_id: UUID
    user_id: UUID
    user_email: str


class AcceptInvitation:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: AcceptInvitationCommand,
    ) -> Membership:
        user_email = command.user_email.strip().lower()
        now = datetime.now(UTC)

        async with self._unit_of_work as uow:
            invitation = await uow.invitations.get_by_id(command.invitation_id)

            if invitation is None:
                raise InvitationNotFoundError

            if invitation.status is not InvitationStatus.PENDING:
                raise InvitationNotPendingError

            if invitation.expires_at <= now:
                invitation.status = InvitationStatus.EXPIRED

                await uow.commit()

                raise InvitationExpiredError

            if invitation.email.lower() != user_email:
                raise InvitationEmailMismatchError

            existing_membership = await uow.memberships.get_by_user_and_tenant(
                command.user_id,
                invitation.tenant_id,
            )

            if existing_membership is not None:
                raise UserAlreadyMemberError

            membership = Membership(
                tenant_id=invitation.tenant_id,
                user_id=command.user_id,
                role_id=invitation.role_id,
                status=MembershipStatus.ACTIVE,
            )

            uow.memberships.add(membership)

            invitation.status = InvitationStatus.ACCEPTED
            invitation.accepted_at = now

            await uow.flush()
            await uow.commit()

            return membership
