from dataclasses import dataclass
from uuid import UUID

from app.modules.identity.application.ports.unit_of_work import UnitOfWork
from app.modules.identity.domain.enums import MembershipStatus
from app.modules.identity.infrastructure.models.tenant import Tenant


@dataclass(frozen=True, slots=True)
class UserTenant:
    tenant: Tenant
    membership_id: UUID
    role_id: UUID


class ListUserTenants:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        user_id: UUID,
    ) -> list[UserTenant]:
        async with self._unit_of_work as uow:
            memberships = await uow.memberships.list_by_user(user_id)

            results: list[UserTenant] = []

            for membership in memberships:
                if membership.status is not MembershipStatus.ACTIVE:
                    continue

                tenant = await uow.tenants.get_by_id(membership.tenant_id)

                if tenant is None:
                    continue

                results.append(
                    UserTenant(
                        tenant=tenant,
                        membership_id=membership.id,
                        role_id=membership.role_id,
                    )
                )

            return results
