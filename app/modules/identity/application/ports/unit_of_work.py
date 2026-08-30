from types import TracebackType
from typing import Protocol

from app.modules.identity.application.ports.auth_session_repository import (
    AuthSessionRepository,
)
from app.modules.identity.application.ports.invitation_repository import (
    InvitationRepository,
)
from app.modules.identity.application.ports.membership_repository import (
    MembershipRepository,
)
from app.modules.identity.application.ports.permission_repository import (
    PermissionRepository,
)
from app.modules.identity.application.ports.role_permission_repository import (
    RolePermissionRepository,
)
from app.modules.identity.application.ports.role_repository import (
    RoleRepository,
)
from app.modules.identity.application.ports.tenant_repository import (
    TenantRepository,
)
from app.modules.identity.application.ports.user_repository import UserRepository
from app.modules.ledger.application.ports.repositories import (
    LedgerAccountRepository,
)


class UnitOfWork(Protocol):
    @property
    def users(self) -> UserRepository: ...

    @property
    def auth_sessions(self) -> AuthSessionRepository: ...

    async def __aenter__(self) -> "UnitOfWork": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def flush(self) -> None: ...

    @property
    def tenants(self) -> TenantRepository: ...

    @property
    def memberships(self) -> MembershipRepository: ...

    @property
    def roles(self) -> RoleRepository: ...

    @property
    def permissions(self) -> PermissionRepository: ...

    @property
    def role_permissions(self) -> RolePermissionRepository: ...

    @property
    def invitations(self) -> InvitationRepository: ...

    @property
    def ledger_accounts(self) -> LedgerAccountRepository: ...
