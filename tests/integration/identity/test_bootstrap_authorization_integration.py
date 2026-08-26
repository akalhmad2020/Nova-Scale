import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.identity.application.use_cases.bootstrap_authorization import (
    BootstrapAuthorization,
)
from app.modules.identity.domain.permissions import PERMISSION_CATALOG
from app.modules.identity.domain.roles import DEFAULT_ROLES
from app.modules.identity.infrastructure.models.permission import Permission
from app.modules.identity.infrastructure.models.role import Role
from app.modules.identity.infrastructure.models.role_permission import (
    RolePermission,
)
from app.modules.identity.infrastructure.unit_of_work import (
    SQLAlchemyUnitOfWork,
)


@pytest.mark.integration
async def test_bootstrap_authorization_is_persisted_and_idempotent(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    use_case = BootstrapAuthorization(SQLAlchemyUnitOfWork(session_factory))

    await use_case.execute()
    await use_case.execute()

    expected_permission_codes = {definition.code for definition in PERMISSION_CATALOG}

    expected_role_names = {definition.name for definition in DEFAULT_ROLES}

    async with session_factory() as session:
        permissions = (
            (
                await session.execute(
                    select(Permission).where(Permission.code.in_(expected_permission_codes))
                )
            )
            .scalars()
            .all()
        )

        roles = (
            (await session.execute(select(Role).where(Role.name.in_(expected_role_names))))
            .scalars()
            .all()
        )

        assert {permission.code for permission in permissions} == expected_permission_codes

        assert {role.name for role in roles} == expected_role_names

        permission_count = await session.scalar(
            select(func.count())
            .select_from(Permission)
            .where(Permission.code.in_(expected_permission_codes))
        )

        role_count = await session.scalar(
            select(func.count()).select_from(Role).where(Role.name.in_(expected_role_names))
        )

        assert permission_count == len(expected_permission_codes)
        assert role_count == len(expected_role_names)

        owner = await session.scalar(select(Role).where(Role.name == "owner"))

        assert owner is not None

        owner_permission_count = await session.scalar(
            select(func.count())
            .select_from(RolePermission)
            .where(RolePermission.role_id == owner.id)
        )

        owner_definition = next(role for role in DEFAULT_ROLES if role.name == "owner")

        assert owner_permission_count == len(owner_definition.permissions)
