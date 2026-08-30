from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.identity.infrastructure.repositories.auth_session_repository import (
    AuthSessionRepository as SQLAlchemyAuthSessionRepository,
)
from app.modules.identity.infrastructure.repositories.invitation_repository import (
    InvitationRepository as SQLAlchemyInvitationRepository,
)
from app.modules.identity.infrastructure.repositories.membership_repository import (
    MembershipRepository as SQLAlchemyMembershipRepository,
)
from app.modules.identity.infrastructure.repositories.permission_repository import (
    PermissionRepository as SQLAlchemyPermissionRepository,
)
from app.modules.identity.infrastructure.repositories.role_permission_repository import (
    RolePermissionRepository as SQLAlchemyRolePermissionRepository,
)
from app.modules.identity.infrastructure.repositories.role_repository import (
    RoleRepository as SQLAlchemyRoleRepository,
)
from app.modules.identity.infrastructure.repositories.tenant_repository import (
    TenantRepository as SQLAlchemyTenantRepository,
)
from app.modules.identity.infrastructure.repositories.user_repository import (
    UserRepository as SQLAlchemyUserRepository,
)
from app.modules.ledger.infrastructure.repositories import (
    SQLAlchemyLedgerAccountRepository,
)


class SQLAlchemyUnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

        self._users: SQLAlchemyUserRepository | None = None
        self._auth_sessions: SQLAlchemyAuthSessionRepository | None = None
        self._tenants: SQLAlchemyTenantRepository | None = None
        self._memberships: SQLAlchemyMembershipRepository | None = None
        self._roles: SQLAlchemyRoleRepository | None = None
        self._permissions: SQLAlchemyPermissionRepository | None = None
        self._role_permissions: SQLAlchemyRolePermissionRepository | None = None
        self._invitations: SQLAlchemyInvitationRepository | None = None
        self._ledger_accounts: SQLAlchemyLedgerAccountRepository | None = None

    @property
    def users(self) -> SQLAlchemyUserRepository:
        if self._users is None:
            raise RuntimeError("Unit of work is not active")

        return self._users

    @property
    def auth_sessions(self) -> SQLAlchemyAuthSessionRepository:
        if self._auth_sessions is None:
            raise RuntimeError("Unit of work is not active")

        return self._auth_sessions

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        session = self._session_factory()

        self._session = session
        self._tenants = SQLAlchemyTenantRepository(session)
        self._memberships = SQLAlchemyMembershipRepository(session)
        self._users = SQLAlchemyUserRepository(session)
        self._auth_sessions = SQLAlchemyAuthSessionRepository(session)
        self._roles = SQLAlchemyRoleRepository(session)
        self._permissions = SQLAlchemyPermissionRepository(session)
        self._role_permissions = SQLAlchemyRolePermissionRepository(session)
        self._invitations = SQLAlchemyInvitationRepository(session)
        self._ledger_accounts = SQLAlchemyLedgerAccountRepository(session)

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        session = self._session

        self._tenants = None
        self._memberships = None
        self._roles = None
        self._permissions = None
        self._role_permissions = None
        self._invitations = None
        self._ledger_accounts = None

        if session is None:
            return

        try:
            if exc_type is not None:
                await session.rollback()
        finally:
            await session.close()
            self._session = None
            self._users = None
            self._auth_sessions = None

    async def flush(self) -> None:
        session = self._get_session()
        await session.flush()

    async def commit(self) -> None:
        session = self._get_session()
        await session.commit()

    async def rollback(self) -> None:
        session = self._get_session()
        await session.rollback()

    def _get_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")

        return self._session

    @property
    def tenants(self) -> SQLAlchemyTenantRepository:
        if self._tenants is None:
            raise RuntimeError("Unit of work is not active")

        return self._tenants

    @property
    def memberships(self) -> SQLAlchemyMembershipRepository:
        if self._memberships is None:
            raise RuntimeError("Unit of work is not active")

        return self._memberships

    @property
    def roles(self) -> SQLAlchemyRoleRepository:
        if self._roles is None:
            raise RuntimeError("Unit of work is not active")

        return self._roles

    @property
    def permissions(self) -> SQLAlchemyPermissionRepository:
        if self._permissions is None:
            raise RuntimeError("Unit of work is not active")

        return self._permissions

    @property
    def role_permissions(self) -> SQLAlchemyRolePermissionRepository:
        if self._role_permissions is None:
            raise RuntimeError("Unit of work is not active")

        return self._role_permissions

    @property
    def invitations(self) -> SQLAlchemyInvitationRepository:
        if self._invitations is None:
            raise RuntimeError("Unit of work is not active")

        return self._invitations

    @property
    def ledger_accounts(self) -> SQLAlchemyLedgerAccountRepository:
        if self._ledger_accounts is None:
            raise RuntimeError("Unit of work is not active")

        return self._ledger_accounts
