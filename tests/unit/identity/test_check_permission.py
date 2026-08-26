from uuid import uuid4

import pytest

from app.modules.identity.application.exceptions import PermissionDeniedError
from app.modules.identity.application.use_cases.check_permission import (
    CheckPermission,
    CheckPermissionQuery,
)
from app.modules.identity.infrastructure.models.permission import Permission
from app.modules.identity.infrastructure.models.role import Role
from app.modules.identity.infrastructure.models.role_permission import RolePermission
from tests.unit.identity.fakes import FakeUnitOfWork


async def test_allows_role_with_required_permission() -> None:
    uow = FakeUnitOfWork()

    role = Role(
        name="admin",
        description="Administrator",
    )

    permission = Permission(
        code="shipment:create",
        description="Create shipments",
    )

    uow.roles.add(role)
    uow.permissions.add(permission)

    uow.role_permissions.add(
        RolePermission(
            role_id=role.id,
            permission_id=permission.id,
        )
    )

    use_case = CheckPermission(uow)

    await use_case.execute(
        CheckPermissionQuery(
            role_id=role.id,
            permission_code="shipment:create",
        )
    )


async def test_rejects_role_without_required_permission() -> None:
    uow = FakeUnitOfWork()

    role = Role(
        name="viewer",
        description="Read-only user",
    )

    permission = Permission(
        code="shipment:create",
        description="Create shipments",
    )

    uow.roles.add(role)
    uow.permissions.add(permission)

    use_case = CheckPermission(uow)

    with pytest.raises(PermissionDeniedError):
        await use_case.execute(
            CheckPermissionQuery(
                role_id=role.id,
                permission_code="shipment:create",
            )
        )


async def test_rejects_unknown_permission_code() -> None:
    uow = FakeUnitOfWork()

    role = Role(
        name="operator",
        description="Operator",
    )

    uow.roles.add(role)

    use_case = CheckPermission(uow)

    with pytest.raises(PermissionDeniedError):
        await use_case.execute(
            CheckPermissionQuery(
                role_id=role.id,
                permission_code=f"unknown:{uuid4()}",
            )
        )
