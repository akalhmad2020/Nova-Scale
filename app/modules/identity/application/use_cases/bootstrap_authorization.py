from app.modules.identity.application.ports.unit_of_work import UnitOfWork
from app.modules.identity.domain.permissions import PERMISSION_CATALOG
from app.modules.identity.domain.roles import DEFAULT_ROLES
from app.modules.identity.infrastructure.models.permission import Permission
from app.modules.identity.infrastructure.models.role import Role
from app.modules.identity.infrastructure.models.role_permission import (
    RolePermission,
)


class BootstrapAuthorization:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self) -> None:
        async with self._unit_of_work as uow:
            for definition in PERMISSION_CATALOG:
                permission = await uow.permissions.get_by_code(
                    definition.code,
                )

                if permission is None:
                    uow.permissions.add(
                        Permission(
                            code=definition.code,
                            description=definition.description,
                        )
                    )

            await uow.flush()

            for role_definition in DEFAULT_ROLES:
                role = await uow.roles.get_by_name(
                    role_definition.name,
                )

                if role is None:
                    role = Role(
                        name=role_definition.name,
                        description=role_definition.description,
                    )

                    uow.roles.add(role)
                    await uow.flush()

                desired_permission_codes = set(
                    role_definition.permissions,
                )

                current_permission_codes = await uow.role_permissions.list_permission_codes(
                    role.id,
                )

                missing_permission_codes = desired_permission_codes - current_permission_codes

                obsolete_permission_codes = current_permission_codes - desired_permission_codes

                for permission_code in missing_permission_codes:
                    permission = await uow.permissions.get_by_code(
                        permission_code,
                    )

                    if permission is None:
                        continue

                    uow.role_permissions.add(
                        RolePermission(
                            role_id=role.id,
                            permission_id=permission.id,
                        )
                    )

                for permission_code in obsolete_permission_codes:
                    await uow.role_permissions.remove_permission(
                        role.id,
                        permission_code,
                    )

            await uow.commit()
