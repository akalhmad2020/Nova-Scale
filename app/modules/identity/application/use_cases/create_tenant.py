from dataclasses import dataclass
from uuid import UUID

from app.modules.identity.application.exceptions import (
    TenantSlugAlreadyExistsError,
)
from app.modules.identity.application.ports.unit_of_work import UnitOfWork
from app.modules.identity.domain.enums import (
    MembershipStatus,
    TenantStatus,
)
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.tenant import Tenant


@dataclass(frozen=True)
class CreateTenantCommand:
    user_id: UUID
    name: str
    slug: str


@dataclass(frozen=True)
class CreateTenantResult:
    tenant_id: UUID
    membership_id: UUID
    name: str
    slug: str


class CreateTenant:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: CreateTenantCommand,
    ) -> CreateTenantResult:
        name = command.name.strip()
        slug = command.slug.strip().lower()

        async with self._unit_of_work as uow:
            existing_tenant = await uow.tenants.get_by_slug(slug)

            if existing_tenant is not None:
                raise TenantSlugAlreadyExistsError

            owner_role = await uow.roles.get_by_name("owner")

            if owner_role is None:
                raise RuntimeError("Owner role is not configured")

            tenant = Tenant(
                name=name,
                slug=slug,
                status=TenantStatus.ACTIVE,
            )

            uow.tenants.add(tenant)

            await uow.flush()

            membership = Membership(
                tenant_id=tenant.id,
                user_id=command.user_id,
                role_id=owner_role.id,
                status=MembershipStatus.ACTIVE,
            )

            uow.memberships.add(membership)

            await uow.flush()
            await uow.commit()

            return CreateTenantResult(
                tenant_id=tenant.id,
                membership_id=membership.id,
                name=tenant.name,
                slug=tenant.slug,
            )
