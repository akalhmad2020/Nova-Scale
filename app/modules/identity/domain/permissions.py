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

    CUSTOMER_READ = "customer:read"
    CUSTOMER_CREATE = "customer:create"
    CUSTOMER_UPDATE = "customer:update"
    CUSTOMER_DELETE = "customer:delete"

    LOCATION_READ = "location:read"
    LOCATION_CREATE = "location:create"
    LOCATION_UPDATE = "location:update"
    LOCATION_DELETE = "location:delete"

    SHIPMENT_READ = "shipment:read"
    SHIPMENT_CREATE = "shipment:create"
    SHIPMENT_UPDATE = "shipment:update"
    SHIPMENT_DELETE = "shipment:delete"
    SHIPMENT_TRANSITION = "shipment:transition"


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
    PermissionDefinition(
        code=Permissions.CUSTOMER_READ,
        description="Read customers",
    ),
    PermissionDefinition(
        code=Permissions.CUSTOMER_CREATE,
        description="Create customers",
    ),
    PermissionDefinition(
        code=Permissions.CUSTOMER_UPDATE,
        description="Update customers",
    ),
    PermissionDefinition(
        code=Permissions.CUSTOMER_DELETE,
        description="Delete customers",
    ),
    PermissionDefinition(
        code=Permissions.LOCATION_READ,
        description="Read locations",
    ),
    PermissionDefinition(
        code=Permissions.LOCATION_CREATE,
        description="Create locations",
    ),
    PermissionDefinition(
        code=Permissions.LOCATION_UPDATE,
        description="Update locations",
    ),
    PermissionDefinition(
        code=Permissions.LOCATION_DELETE,
        description="Delete locations",
    ),
    PermissionDefinition(
        code=Permissions.SHIPMENT_READ,
        description="Read shipments",
    ),
    PermissionDefinition(
        code=Permissions.SHIPMENT_CREATE,
        description="Create shipments",
    ),
    PermissionDefinition(
        code=Permissions.SHIPMENT_UPDATE,
        description="Update shipments",
    ),
    PermissionDefinition(
        code=Permissions.SHIPMENT_DELETE,
        description="Delete shipments",
    ),
    PermissionDefinition(
        code=Permissions.SHIPMENT_TRANSITION,
        description="Transition shipment status",
    ),
)
