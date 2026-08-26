from dataclasses import dataclass
from uuid import UUID

from app.modules.identity.application.exceptions import (
    InactiveMembershipError,
    InactiveTenantError,
    MembershipNotFoundError,
    TenantNotFoundError,
)
from app.modules.identity.application.ports.unit_of_work import UnitOfWork
from app.modules.identity.domain.enums import (
    MembershipStatus,
    TenantStatus,
)
from app.modules.identity.infrastructure.models.membership import Membership


@dataclass(frozen=True, slots=True)
class GetActiveMembershipQuery:
    user_id: UUID
    tenant_id: UUID


class GetActiveMembership:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: GetActiveMembershipQuery,
    ) -> Membership:
        async with self._unit_of_work as uow:
            tenant = await uow.tenants.get_by_id(query.tenant_id)

            if tenant is None:
                raise TenantNotFoundError

            if tenant.status is not TenantStatus.ACTIVE:
                raise InactiveTenantError

            membership = await uow.memberships.get_by_user_and_tenant(
                query.user_id,
                query.tenant_id,
            )

            if membership is None:
                raise MembershipNotFoundError

            if membership.status is not MembershipStatus.ACTIVE:
                raise InactiveMembershipError

            return membership
