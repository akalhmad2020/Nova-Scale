from app.modules.identity.application.use_cases.bootstrap_authorization import (
    BootstrapAuthorization,
)
from app.modules.identity.domain.permissions import (
    PERMISSION_CATALOG,
    Permissions,
)
from app.modules.identity.domain.roles import DEFAULT_ROLES
from tests.unit.identity.fakes import FakeUnitOfWork


async def test_bootstrap_creates_permission_catalog() -> None:
    uow = FakeUnitOfWork()

    use_case = BootstrapAuthorization(uow)

    await use_case.execute()

    codes = {permission.code for permission in uow.permissions.permissions}

    expected_codes = {definition.code for definition in PERMISSION_CATALOG}

    assert codes == expected_codes


async def test_bootstrap_creates_default_roles() -> None:
    uow = FakeUnitOfWork()

    use_case = BootstrapAuthorization(uow)

    await use_case.execute()

    role_names = {role.name for role in uow.roles.roles}

    expected_role_names = {definition.name for definition in DEFAULT_ROLES}

    assert role_names == expected_role_names


async def test_bootstrap_assigns_permissions_to_owner() -> None:
    uow = FakeUnitOfWork()

    use_case = BootstrapAuthorization(uow)

    await use_case.execute()

    owner = await uow.roles.get_by_name("owner")

    assert owner is not None

    assert await uow.role_permissions.has_permission(
        owner.id,
        Permissions.TENANT_READ,
    )

    assert await uow.role_permissions.has_permission(
        owner.id,
        Permissions.TENANT_MANAGE,
    )

    assert await uow.role_permissions.has_permission(
        owner.id,
        Permissions.MEMBERSHIP_MANAGE,
    )

    assert await uow.role_permissions.has_permission(
        owner.id,
        Permissions.ROLE_MANAGE,
    )


async def test_bootstrap_is_idempotent() -> None:
    uow = FakeUnitOfWork()

    use_case = BootstrapAuthorization(uow)

    await use_case.execute()

    permission_count = len(uow.permissions.permissions)
    role_count = len(uow.roles.roles)
    role_permission_count = len(uow.role_permissions.role_permissions)

    await use_case.execute()

    assert len(uow.permissions.permissions) == permission_count
    assert len(uow.roles.roles) == role_count

    assert len(uow.role_permissions.role_permissions) == role_permission_count


async def test_bootstrap_commits_transaction() -> None:
    uow = FakeUnitOfWork()

    use_case = BootstrapAuthorization(uow)

    await use_case.execute()

    assert uow.committed is True
