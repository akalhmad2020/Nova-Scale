from dataclasses import dataclass
from uuid import UUID

from app.modules.identity.application.exceptions import (
    CannotSuspendLastOwnerError,
    CannotSuspendSelfError,
    MembershipNotFoundError,
    MembershipTenantMismatchError,
)
from app.modules.identity.application.ports.unit_of_work import UnitOfWork
from app.modules.identity.domain.enums import MembershipStatus
from app.modules.identity.infrastructure.models.membership import Membership


@dataclass(frozen=True, slots=True)
class SuspendMembershipCommand:
    tenant_id: UUID
    membership_id: UUID
    actor_user_id: UUID


class SuspendMembership:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: SuspendMembershipCommand,
    ) -> Membership:
        async with self._unit_of_work as uow:
            membership = await uow.memberships.get_by_id(command.membership_id)

            if membership is None:
                raise MembershipNotFoundError

            if membership.tenant_id != command.tenant_id:
                raise MembershipTenantMismatchError

            if membership.user_id == command.actor_user_id:
                raise CannotSuspendSelfError

            if membership.status is MembershipStatus.SUSPENDED:
                return membership

            owner_role = await uow.roles.get_by_name("owner")

            if owner_role is None:
                raise RuntimeError("Owner role is not configured")

            if membership.role_id == owner_role.id:
                memberships = await uow.memberships.list_by_tenant(command.tenant_id)

                active_owner_count = sum(
                    1
                    for item in memberships
                    if item.role_id == owner_role.id and item.status is MembershipStatus.ACTIVE
                )

                if active_owner_count <= 1:
                    raise CannotSuspendLastOwnerError

            membership.status = MembershipStatus.SUSPENDED

            await uow.flush()
            await uow.commit()

            return membership
