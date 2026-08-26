from dataclasses import dataclass

from app.modules.identity.domain.permissions import Permissions


@dataclass(frozen=True, slots=True)
class RoleDefinition:
    name: str
    description: str
    permissions: tuple[str, ...]


DEFAULT_ROLES = (
    RoleDefinition(
        name="owner",
        description="Tenant owner with full administrative access",
        permissions=(
            Permissions.TENANT_READ,
            Permissions.TENANT_MANAGE,
            Permissions.MEMBERSHIP_READ,
            Permissions.MEMBERSHIP_MANAGE,
            Permissions.ROLE_READ,
            Permissions.ROLE_MANAGE,
        ),
    ),
    RoleDefinition(
        name="admin",
        description="Tenant administrator",
        permissions=(
            Permissions.TENANT_READ,
            Permissions.MEMBERSHIP_READ,
            Permissions.MEMBERSHIP_MANAGE,
            Permissions.ROLE_READ,
        ),
    ),
    RoleDefinition(
        name="member",
        description="Standard tenant member",
        permissions=(
            Permissions.TENANT_READ,
            Permissions.MEMBERSHIP_READ,
        ),
    ),
)
