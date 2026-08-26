from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PermissionDefinition:
    code: str
    description: str


class Permissions:
    TENANT_READ = "tenant:read"
    TENANT_MANAGE = "tenant:manage"

    MEMBERSHIP_READ = "membership:read"
    MEMBERSHIP_MANAGE = "membership:manage"

    ROLE_READ = "role:read"
    ROLE_MANAGE = "role:manage"


PERMISSION_CATALOG = (
    PermissionDefinition(
        code=Permissions.TENANT_READ,
        description="Read tenant information",
    ),
    PermissionDefinition(
        code=Permissions.TENANT_MANAGE,
        description="Manage tenant settings",
    ),
    PermissionDefinition(
        code=Permissions.MEMBERSHIP_READ,
        description="Read tenant memberships",
    ),
    PermissionDefinition(
        code=Permissions.MEMBERSHIP_MANAGE,
        description="Manage tenant memberships",
    ),
    PermissionDefinition(
        code=Permissions.ROLE_READ,
        description="Read roles and permissions",
    ),
    PermissionDefinition(
        code=Permissions.ROLE_MANAGE,
        description="Manage roles and permissions",
    ),
)
