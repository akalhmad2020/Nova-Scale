from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.modules.identity.application.exceptions import (
    CannotRemoveLastOwnerError,
    CannotRemoveSelfError,
    MembershipNotFoundError,
    MembershipTenantMismatchError,
)
from app.modules.identity.application.ports.unit_of_work import UnitOfWork
from app.modules.identity.domain.enums import MembershipStatus


@dataclass(frozen=True, slots=True)
class RemoveMembershipCommand:
    tenant_id: UUID
    membership_id: UUID
    actor_user_id: UUID


class RemoveMembership:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: RemoveMembershipCommand,
    ) -> None:
        async with self._unit_of_work as uow:
            membership = await uow.memberships.get_by_id(command.membership_id)

            if membership is None:
                raise MembershipNotFoundError

            if membership.tenant_id != command.tenant_id:
                raise MembershipTenantMismatchError

            if membership.user_id == command.actor_user_id:
                raise CannotRemoveSelfError

            owner_role = await uow.roles.get_by_name("owner")

            if owner_role is None:
                raise RuntimeError("Owner role is not configured")

            if membership.role_id == owner_role.id and membership.status is MembershipStatus.ACTIVE:
                memberships = await uow.memberships.list_by_tenant(command.tenant_id)

                active_owner_count = sum(
                    1
                    for item in memberships
                    if item.role_id == owner_role.id
                    and item.status is MembershipStatus.ACTIVE
                    and item.deleted_at is None
                )

                if active_owner_count <= 1:
                    raise CannotRemoveLastOwnerError

            if membership.deleted_at is not None:
                return

            membership.deleted_at = datetime.now(UTC)

            await uow.flush()
            await uow.commit()
