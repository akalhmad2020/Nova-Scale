from dataclasses import dataclass
from uuid import UUID

from app.modules.identity.application.exceptions import (
    MembershipNotFoundError,
    MembershipTenantMismatchError,
    RoleNotFoundError,
)
from app.modules.identity.application.ports.unit_of_work import UnitOfWork
from app.modules.identity.infrastructure.models.membership import Membership


@dataclass(frozen=True, slots=True)
class ChangeMemberRoleCommand:
    tenant_id: UUID
    membership_id: UUID
    role_id: UUID


class ChangeMemberRole:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: ChangeMemberRoleCommand,
    ) -> Membership:
        async with self._unit_of_work as uow:
            membership = await uow.memberships.get_by_id(command.membership_id)

            if membership is None:
                raise MembershipNotFoundError

            if membership.tenant_id != command.tenant_id:
                raise MembershipTenantMismatchError

            role = await uow.roles.get_by_id(command.role_id)

            if role is None:
                raise RoleNotFoundError

            membership.role_id = role.id

            await uow.flush()
            await uow.commit()

            return membership
