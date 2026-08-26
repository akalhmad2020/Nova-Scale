from dataclasses import dataclass
from uuid import UUID

from app.modules.identity.application.ports.unit_of_work import UnitOfWork
from app.modules.identity.domain.enums import MembershipStatus
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.user import User


@dataclass(frozen=True, slots=True)
class TenantMember:
    membership: Membership
    user: User


class ListTenantMembers:
    def __init__(
        self,
        uow: UnitOfWork,
    ) -> None:
        self._uow = uow

    async def execute(
        self,
        tenant_id: UUID,
    ) -> list[TenantMember]:
        async with self._uow as uow:
            memberships = await uow.memberships.list_by_tenant(tenant_id)

            members: list[TenantMember] = []

            for membership in memberships:
                if membership.status is not MembershipStatus.ACTIVE:
                    continue

                user = await uow.users.get_by_id(membership.user_id)

                if user is None:
                    continue

                members.append(
                    TenantMember(
                        membership=membership,
                        user=user,
                    )
                )

            return members
