from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.modules.identity.application.exceptions import (
    InvitationAlreadyPendingError,
    RoleNotFoundError,
    UserAlreadyMemberError,
)
from app.modules.identity.application.ports.invitation_token_service import (
    InvitationTokenService,
)
from app.modules.identity.application.ports.unit_of_work import UnitOfWork
from app.modules.identity.domain.enums import InvitationStatus
from app.modules.identity.infrastructure.models.invitation import Invitation


@dataclass(frozen=True, slots=True)
class InviteMemberCommand:
    tenant_id: UUID
    email: str
    role_id: UUID


@dataclass(frozen=True, slots=True)
class InviteMemberResult:
    invitation_id: UUID
    email: str
    tenant_id: UUID
    role_id: UUID
    expires_at: datetime
    token: str


class InviteMember:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        invitation_token_service: InvitationTokenService,
        invitation_ttl_days: int = 7,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._invitation_token_service = invitation_token_service
        self._invitation_ttl_days = invitation_ttl_days

    async def execute(
        self,
        command: InviteMemberCommand,
    ) -> InviteMemberResult:
        email = command.email.strip().lower()

        async with self._unit_of_work as uow:
            role = await uow.roles.get_by_id(command.role_id)

            if role is None:
                raise RoleNotFoundError

            existing_user = await uow.users.get_by_email(email)

            if existing_user is not None:
                existing_membership = await uow.memberships.get_by_user_and_tenant(
                    existing_user.id,
                    command.tenant_id,
                )

                if existing_membership is not None:
                    raise UserAlreadyMemberError

            pending_invitation = await uow.invitations.get_pending_by_email_and_tenant(
                email,
                command.tenant_id,
            )

            if pending_invitation is not None:
                raise InvitationAlreadyPendingError

            token = self._invitation_token_service.generate_token()
            token_hash = self._invitation_token_service.hash_token(token)

            invitation = Invitation(
                tenant_id=command.tenant_id,
                role_id=command.role_id,
                email=email,
                token_hash=token_hash,
                status=InvitationStatus.PENDING,
                expires_at=datetime.now(UTC) + timedelta(days=self._invitation_ttl_days),
            )

            uow.invitations.add(invitation)

            await uow.flush()
            await uow.commit()

            return InviteMemberResult(
                invitation_id=invitation.id,
                email=invitation.email,
                tenant_id=invitation.tenant_id,
                role_id=invitation.role_id,
                expires_at=invitation.expires_at,
                token=token,
            )
