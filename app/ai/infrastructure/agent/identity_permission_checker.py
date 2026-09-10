from uuid import UUID

from app.modules.identity.application.exceptions import (
    PermissionDeniedError,
)
from app.modules.identity.application.use_cases.check_permission import (
    CheckPermission,
    CheckPermissionQuery,
)


class IdentityPermissionChecker:
    def __init__(
        self,
        *,
        check_permission: CheckPermission,
    ) -> None:
        self._check_permission = check_permission

    async def __call__(
        self,
        role_id: UUID,
        permission_code: str,
    ) -> bool:
        try:
            await self._check_permission.execute(
                CheckPermissionQuery(
                    role_id=role_id,
                    permission_code=permission_code,
                )
            )
        except PermissionDeniedError:
            return False

        return True
