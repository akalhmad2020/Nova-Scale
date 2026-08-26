from dataclasses import dataclass
from uuid import UUID

from app.modules.identity.application.exceptions import PermissionDeniedError
from app.modules.identity.application.ports.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class CheckPermissionQuery:
    role_id: UUID
    permission_code: str


class CheckPermission:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: CheckPermissionQuery,
    ) -> None:
        async with self._unit_of_work as uow:
            has_permission = await uow.role_permissions.has_permission(
                query.role_id,
                query.permission_code,
            )

            if not has_permission:
                raise PermissionDeniedError
