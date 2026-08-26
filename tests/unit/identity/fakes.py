from types import TracebackType
from uuid import UUID

from app.modules.identity.domain.enums import InvitationStatus
from app.modules.identity.infrastructure.models.auth_session import AuthSession
from app.modules.identity.infrastructure.models.invitation import Invitation
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.permission import Permission
from app.modules.identity.infrastructure.models.role import Role
from app.modules.identity.infrastructure.models.role_permission import (
    RolePermission,
)
from app.modules.identity.infrastructure.models.tenant import Tenant
from app.modules.identity.infrastructure.models.user import User


class FakeUserRepository:
    def __init__(self) -> None:
        self.users: list[User] = []

    async def get_by_id(self, user_id: UUID) -> User | None:
        return next(
            (user for user in self.users if user.id == user_id and user.deleted_at is None),
            None,
        )

    async def get_by_email(self, email: str) -> User | None:
        return next(
            (
                user
                for user in self.users
                if user.email.lower() == email.lower() and user.deleted_at is None
            ),
            None,
        )

    async def email_exists(self, email: str) -> bool:
        return await self.get_by_email(email) is not None

    def add(self, user: User) -> None:
        self.users.append(user)


class FakeAuthSessionRepository:
    def __init__(self) -> None:
        self.sessions: list[AuthSession] = []

    async def get_by_id(
        self,
        session_id: UUID,
    ) -> AuthSession | None:
        return next(
            (session for session in self.sessions if session.id == session_id),
            None,
        )

    async def get_by_refresh_token_hash(
        self,
        refresh_token_hash: str,
    ) -> AuthSession | None:
        return next(
            (
                session
                for session in self.sessions
                if session.refresh_token_hash == refresh_token_hash
            ),
            None,
        )

    async def get_by_refresh_token_hash_for_update(
        self,
        refresh_token_hash: str,
    ) -> AuthSession | None:
        return await self.get_by_refresh_token_hash(refresh_token_hash)

    def add(self, auth_session: AuthSession) -> None:
        self.sessions.append(auth_session)


class FakeTenantRepository:
    def __init__(self) -> None:
        self.tenants: list[Tenant] = []

    async def get_by_id(
        self,
        tenant_id: UUID,
    ) -> Tenant | None:
        return next(
            (
                tenant
                for tenant in self.tenants
                if tenant.id == tenant_id and tenant.deleted_at is None
            ),
            None,
        )

    async def get_by_slug(
        self,
        slug: str,
    ) -> Tenant | None:
        return next(
            (
                tenant
                for tenant in self.tenants
                if tenant.slug == slug and tenant.deleted_at is None
            ),
            None,
        )

    def add(self, tenant: Tenant) -> None:
        self.tenants.append(tenant)


class FakeMembershipRepository:
    def __init__(self) -> None:
        self.memberships: list[Membership] = []

    async def get_by_id(
        self,
        membership_id: UUID,
    ) -> Membership | None:
        return next(
            (
                membership
                for membership in self.memberships
                if membership.id == membership_id and membership.deleted_at is None
            ),
            None,
        )

    async def get_by_user_and_tenant(
        self,
        user_id: UUID,
        tenant_id: UUID,
    ) -> Membership | None:
        return next(
            (
                membership
                for membership in self.memberships
                if membership.user_id == user_id
                and membership.tenant_id == tenant_id
                and membership.deleted_at is None
            ),
            None,
        )

    async def list_by_user(
        self,
        user_id: UUID,
    ) -> list[Membership]:
        return [
            membership
            for membership in self.memberships
            if membership.user_id == user_id and membership.deleted_at is None
        ]

    def add(self, membership: Membership) -> None:
        self.memberships.append(membership)

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[Membership]:
        return [
            membership
            for membership in self.memberships
            if membership.tenant_id == tenant_id and membership.deleted_at is None
        ]


class FakeRoleRepository:
    def __init__(self) -> None:
        self.roles: list[Role] = []

    async def get_by_id(
        self,
        role_id: UUID,
    ) -> Role | None:
        return next(
            (role for role in self.roles if role.id == role_id),
            None,
        )

    async def get_by_name(
        self,
        name: str,
    ) -> Role | None:
        return next(
            (role for role in self.roles if role.name == name),
            None,
        )

    def add(self, role: Role) -> None:
        self.roles.append(role)


class FakePermissionRepository:
    def __init__(self) -> None:
        self.permissions: list[Permission] = []

    async def get_by_id(
        self,
        permission_id: UUID,
    ) -> Permission | None:
        return next(
            (permission for permission in self.permissions if permission.id == permission_id),
            None,
        )

    async def get_by_code(
        self,
        code: str,
    ) -> Permission | None:
        return next(
            (permission for permission in self.permissions if permission.code == code),
            None,
        )

    def add(self, permission: Permission) -> None:
        self.permissions.append(permission)


class FakeRolePermissionRepository:
    def __init__(self) -> None:
        self.role_permissions: list[RolePermission] = []
        self.permissions: list[Permission] = []

    async def has_permission(
        self,
        role_id: UUID,
        permission_code: str,
    ) -> bool:
        permission = next(
            (permission for permission in self.permissions if permission.code == permission_code),
            None,
        )

        if permission is None:
            return False

        return any(
            role_permission.role_id == role_id and role_permission.permission_id == permission.id
            for role_permission in self.role_permissions
        )

    def add(
        self,
        role_permission: RolePermission,
    ) -> None:
        self.role_permissions.append(role_permission)


class FakePasswordHasher:
    def hash(self, password: str) -> str:
        return f"hashed::{password}"

    def verify(
        self,
        password: str,
        password_hash: str,
    ) -> bool:
        return password_hash == f"hashed::{password}"

    def needs_rehash(self, password_hash: str) -> bool:
        return False


class FakeInvitationRepository:
    def __init__(self) -> None:
        self.invitations: list[Invitation] = []

    async def get_by_id(
        self,
        invitation_id: UUID,
    ) -> Invitation | None:
        return next(
            (invitation for invitation in self.invitations if invitation.id == invitation_id),
            None,
        )

    async def get_pending_by_email_and_tenant(
        self,
        email: str,
        tenant_id: UUID,
    ) -> Invitation | None:

        return next(
            (
                invitation
                for invitation in self.invitations
                if invitation.email.lower() == email.lower()
                and invitation.tenant_id == tenant_id
                and invitation.status is InvitationStatus.PENDING
            ),
            None,
        )

    def add(
        self,
        invitation: Invitation,
    ) -> None:
        self.invitations.append(invitation)


class FakeUnitOfWork:
    def __init__(self) -> None:
        self._users = FakeUserRepository()
        self._auth_sessions = FakeAuthSessionRepository()
        self._tenants = FakeTenantRepository()
        self._memberships = FakeMembershipRepository()

        self.committed = False
        self.rolled_back = False
        self.flushed = False

        self._roles = FakeRoleRepository()
        self._permissions = FakePermissionRepository()
        self._role_permissions = FakeRolePermissionRepository()
        self._role_permissions.permissions = self._permissions.permissions

        self._invitations = FakeInvitationRepository()

    @property
    def users(self) -> FakeUserRepository:
        return self._users

    @property
    def invitations(self) -> FakeInvitationRepository:
        return self._invitations

    @property
    def auth_sessions(self) -> FakeAuthSessionRepository:
        return self._auth_sessions

    @property
    def tenants(self) -> FakeTenantRepository:
        return self._tenants

    @property
    def memberships(self) -> FakeMembershipRepository:
        return self._memberships

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def flush(self) -> None:
        self.flushed = True

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    @property
    def roles(self) -> FakeRoleRepository:
        return self._roles

    @property
    def permissions(self) -> FakePermissionRepository:
        return self._permissions

    @property
    def role_permissions(self) -> FakeRolePermissionRepository:
        return self._role_permissions
