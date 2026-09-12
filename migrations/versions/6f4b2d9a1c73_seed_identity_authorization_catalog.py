"""seed identity authorization catalog

Revision ID: 6f4b2d9a1c73
Revises: f2c4a91d7b36
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "6f4b2d9a1c73"
down_revision: str | None = "f2c4a91d7b36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PERMISSIONS = (
    (
        "tenant:read",
        "Read tenant information",
    ),
    (
        "tenant:manage",
        "Manage tenant settings",
    ),
    (
        "membership:read",
        "Read tenant memberships",
    ),
    (
        "membership:manage",
        "Manage tenant memberships",
    ),
    (
        "role:read",
        "Read roles and permissions",
    ),
    (
        "role:manage",
        "Manage roles and permissions",
    ),
    (
        "customer:read",
        "Read customers",
    ),
    (
        "customer:create",
        "Create customers",
    ),
    (
        "customer:update",
        "Update customers",
    ),
    (
        "customer:delete",
        "Delete customers",
    ),
    (
        "location:read",
        "Read locations",
    ),
    (
        "location:create",
        "Create locations",
    ),
    (
        "location:update",
        "Update locations",
    ),
    (
        "location:delete",
        "Delete locations",
    ),
    (
        "shipment:read",
        "Read shipments",
    ),
    (
        "shipment:create",
        "Create shipments",
    ),
    (
        "shipment:update",
        "Update shipments",
    ),
    (
        "shipment:delete",
        "Delete shipments",
    ),
    (
        "shipment:transition",
        "Transition shipment status",
    ),
    (
        "package:read",
        "Read packages",
    ),
    (
        "package:create",
        "Create packages",
    ),
    (
        "package:update",
        "Update packages",
    ),
    (
        "package:delete",
        "Delete packages",
    ),
    (
        "shipment_event:read",
        "Read shipment events",
    ),
    (
        "shipment_event:create",
        "Create shipment events",
    ),
    (
        "rate:read",
        "Read rate quotes",
    ),
    (
        "rate:create",
        "Create rate quotes",
    ),
    (
        "rate:manage",
        "Manage rate quote lifecycle",
    ),
    (
        "pricing_rule:read",
        "Read pricing rules",
    ),
    (
        "pricing_rule:create",
        "Create pricing rules",
    ),
    (
        "pricing_rule:update",
        "Update pricing rules",
    ),
    (
        "pricing_rule:delete",
        "Delete pricing rules",
    ),
    (
        "carrier:read",
        "Read carriers",
    ),
    (
        "carrier:create",
        "Create carriers",
    ),
    (
        "carrier:update",
        "Update carriers",
    ),
    (
        "carrier:delete",
        "Delete carriers",
    ),
    (
        "carrier_service:read",
        "Read carrier services",
    ),
    (
        "carrier_service:create",
        "Create carrier services",
    ),
    (
        "carrier_service:update",
        "Update carrier services",
    ),
    (
        "carrier_service:delete",
        "Delete carrier services",
    ),
    (
        "document:read",
        "Read documents",
    ),
    (
        "document:create",
        "Create documents",
    ),
    (
        "document:update",
        "Update document lifecycle",
    ),
    (
        "shipment_label:read",
        "Read shipment labels",
    ),
    (
        "shipment_label:create",
        "Create shipment labels",
    ),
    (
        "shipment_label:update",
        "Update shipment label lifecycle",
    ),
    (
        "shipment_label:void",
        "Void shipment labels",
    ),
    (
        "invoice:read",
        "Read invoices",
    ),
    (
        "invoice:create",
        "Create invoices",
    ),
    (
        "invoice:update",
        "Update draft invoices",
    ),
    (
        "invoice:issue",
        "Issue invoices",
    ),
    (
        "invoice:void",
        "Void invoices",
    ),
    (
        "payment:read",
        "Read payments",
    ),
    (
        "payment:create",
        "Create payments",
    ),
    (
        "payment:update",
        "Update payment allocations",
    ),
    (
        "payment:post",
        "Post payments",
    ),
    (
        "payment:void",
        "Void payments",
    ),
    (
        "subscription:read",
        "Read tenant SaaS subscription",
    ),
    (
        "entitlement:read",
        "Read effective tenant entitlements",
    ),
    (
        "notification:read",
        "Read tenant notification delivery history",
    ),
)


ROLES = (
    (
        "owner",
        "Tenant owner with full administrative access",
    ),
    (
        "admin",
        "Tenant administrator",
    ),
    (
        "member",
        "Standard tenant member",
    ),
)


ROLE_PERMISSIONS = {
    "owner": (
        "tenant:read",
        "tenant:manage",
        "membership:read",
        "membership:manage",
        "role:read",
        "role:manage",
        "customer:read",
        "customer:create",
        "customer:update",
        "customer:delete",
        "location:read",
        "location:create",
        "location:update",
        "location:delete",
        "shipment:read",
        "shipment:create",
        "shipment:update",
        "shipment:transition",
        "package:read",
        "package:create",
        "package:update",
        "package:delete",
        "shipment_event:read",
        "shipment_event:create",
        "rate:read",
        "rate:create",
        "rate:manage",
        "pricing_rule:read",
        "pricing_rule:create",
        "pricing_rule:update",
        "pricing_rule:delete",
        "carrier:read",
        "carrier:create",
        "carrier:update",
        "carrier:delete",
        "carrier_service:read",
        "carrier_service:create",
        "carrier_service:update",
        "carrier_service:delete",
        "document:read",
        "document:create",
        "document:update",
        "shipment_label:read",
        "shipment_label:create",
        "shipment_label:update",
        "shipment_label:void",
        "invoice:read",
        "invoice:create",
        "invoice:update",
        "invoice:issue",
        "invoice:void",
        "payment:read",
        "payment:create",
        "payment:update",
        "payment:post",
        "payment:void",
        "subscription:read",
        "entitlement:read",
        "notification:read",
    ),
    "admin": (
        "tenant:read",
        "membership:read",
        "membership:manage",
        "role:read",
        "customer:read",
        "customer:create",
        "customer:update",
        "customer:delete",
        "location:read",
        "location:create",
        "location:update",
        "location:delete",
        "shipment:read",
        "shipment:create",
        "shipment:update",
        "shipment:transition",
        "package:read",
        "package:create",
        "package:update",
        "package:delete",
        "shipment_event:read",
        "shipment_event:create",
        "rate:read",
        "rate:create",
        "rate:manage",
        "carrier:read",
        "carrier:create",
        "carrier:update",
        "carrier:delete",
        "carrier_service:read",
        "carrier_service:create",
        "carrier_service:update",
        "carrier_service:delete",
        "document:read",
        "document:create",
        "document:update",
        "shipment_label:read",
        "shipment_label:create",
        "shipment_label:update",
        "shipment_label:void",
        "invoice:read",
        "invoice:create",
        "invoice:update",
        "invoice:issue",
        "invoice:void",
        "payment:read",
        "payment:create",
        "payment:update",
        "payment:post",
        "payment:void",
        "subscription:read",
        "entitlement:read",
        "notification:read",
    ),
    "member": (
        "tenant:read",
        "membership:read",
        "customer:read",
        "location:read",
        "shipment:read",
        "package:read",
        "shipment_event:read",
        "rate:read",
        "carrier:read",
        "carrier_service:read",
        "document:read",
        "shipment_label:read",
        "invoice:read",
        "payment:read",
        "subscription:read",
        "entitlement:read",
    ),
}


def upgrade() -> None:
    _validate_catalog()

    connection = op.get_bind()

    permission_statement = sa.text(
        """
        INSERT INTO permissions (
            code,
            description
        )
        VALUES (
            :code,
            :description
        )
        ON CONFLICT (code)
        DO UPDATE
        SET
            description = EXCLUDED.description,
            updated_at = now()
        """
    )

    connection.execute(
        permission_statement,
        [
            {
                "code": code,
                "description": description,
            }
            for code, description in PERMISSIONS
        ],
    )

    role_statement = sa.text(
        """
        INSERT INTO roles (
            name,
            description
        )
        VALUES (
            :name,
            :description
        )
        ON CONFLICT (name)
        DO UPDATE
        SET
            description = EXCLUDED.description,
            updated_at = now()
        """
    )

    connection.execute(
        role_statement,
        [
            {
                "name": name,
                "description": description,
            }
            for name, description in ROLES
        ],
    )

    role_permission_statement = sa.text(
        """
        INSERT INTO role_permissions (
            role_id,
            permission_id
        )
        SELECT
            roles.id,
            permissions.id
        FROM roles
        CROSS JOIN permissions
        WHERE
            roles.name = :role_name
            AND permissions.code = :permission_code
        ON CONFLICT (
            role_id,
            permission_id
        )
        DO NOTHING
        """
    )

    mappings = [
        {
            "role_name": role_name,
            "permission_code": permission_code,
        }
        for role_name, permission_codes in ROLE_PERMISSIONS.items()
        for permission_code in permission_codes
    ]

    connection.execute(
        role_permission_statement,
        mappings,
    )


def downgrade() -> None:
    connection = op.get_bind()

    role_permission_statement = sa.text(
        """
        DELETE FROM role_permissions
        WHERE role_id IN (
            SELECT id
            FROM roles
            WHERE name = :role_name
        )
        AND permission_id IN (
            SELECT id
            FROM permissions
            WHERE code = :permission_code
        )
        """
    )

    mappings = [
        {
            "role_name": role_name,
            "permission_code": permission_code,
        }
        for role_name, permission_codes in ROLE_PERMISSIONS.items()
        for permission_code in permission_codes
    ]

    connection.execute(
        role_permission_statement,
        mappings,
    )

    connection.execute(
        sa.text(
            """
            DELETE FROM roles AS role
            WHERE role.name IN (
                'owner',
                'admin',
                'member'
            )
            AND NOT EXISTS (
                SELECT 1
                FROM memberships
                WHERE memberships.role_id = role.id
            )
            AND NOT EXISTS (
                SELECT 1
                FROM invitations
                WHERE invitations.role_id = role.id
            )
            """
        )
    )

    connection.execute(
        sa.text(
            """
            DELETE FROM permissions AS permission
            WHERE permission.code = ANY(:codes)
            AND NOT EXISTS (
                SELECT 1
                FROM role_permissions
                WHERE role_permissions.permission_id = permission.id
            )
            """
        ),
        {
            "codes": [code for code, _description in PERMISSIONS],
        },
    )


def _validate_catalog() -> None:
    permission_codes = {code for code, _description in PERMISSIONS}

    role_names = {name for name, _description in ROLES}

    configured_role_names = set(ROLE_PERMISSIONS)

    if configured_role_names != role_names:
        raise RuntimeError("Authorization migration role definitions are inconsistent.")

    unknown_permissions = sorted(
        {
            permission_code
            for permission_codes_for_role in ROLE_PERMISSIONS.values()
            for permission_code in permission_codes_for_role
            if permission_code not in permission_codes
        }
    )

    if unknown_permissions:
        raise RuntimeError(
            "Authorization migration contains unknown permissions: "
            + ", ".join(unknown_permissions)
        )
