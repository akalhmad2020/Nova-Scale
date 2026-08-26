from app.core.config import get_settings
from app.core.database import SessionFactory
from app.modules.identity.application.use_cases.accept_invitation import (
    AcceptInvitation,
)
from app.modules.identity.application.use_cases.change_member_role import (
    ChangeMemberRole,
)
from app.modules.identity.application.use_cases.check_permission import (
    CheckPermission,
)
from app.modules.identity.application.use_cases.create_tenant import CreateTenant
from app.modules.identity.application.use_cases.get_active_membership import (
    GetActiveMembership,
)
from app.modules.identity.application.use_cases.invite_member import InviteMember
from app.modules.identity.application.use_cases.list_tenant_members import (
    ListTenantMembers,
)
from app.modules.identity.application.use_cases.list_user_tenants import (
    ListUserTenants,
)
from app.modules.identity.application.use_cases.login_user import LoginUser
from app.modules.identity.application.use_cases.logout_user import LogoutUser
from app.modules.identity.application.use_cases.refresh_session import (
    RefreshSession,
)
from app.modules.identity.application.use_cases.register_user import RegisterUser
from app.modules.identity.application.use_cases.remove_membership import (
    RemoveMembership,
)
from app.modules.identity.application.use_cases.suspend_membership import (
    SuspendMembership,
)
from app.modules.identity.infrastructure.security.access_token_service import (
    JWTAccessTokenService,
)
from app.modules.identity.infrastructure.security.password_hasher import (
    Argon2PasswordHasher,
)
from app.modules.identity.infrastructure.security.refresh_token_service import (
    SecureRefreshTokenService,
)
from app.modules.identity.infrastructure.unit_of_work import (
    SQLAlchemyUnitOfWork,
)


def get_remove_membership_use_case() -> RemoveMembership:
    return RemoveMembership(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_change_member_role_use_case() -> ChangeMemberRole:
    return ChangeMemberRole(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_suspend_membership_use_case() -> SuspendMembership:
    return SuspendMembership(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_list_tenant_members_use_case() -> ListTenantMembers:
    return ListTenantMembers(
        uow=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_register_user_use_case() -> RegisterUser:
    unit_of_work = SQLAlchemyUnitOfWork(SessionFactory)
    password_hasher = Argon2PasswordHasher()

    return RegisterUser(
        unit_of_work=unit_of_work,
        password_hasher=password_hasher,
    )


def get_accept_invitation_use_case() -> AcceptInvitation:
    return AcceptInvitation(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_invite_member_use_case() -> InviteMember:
    return InviteMember(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
        invitation_ttl_days=7,
    )


def get_login_user_use_case() -> LoginUser:
    settings = get_settings()

    unit_of_work = SQLAlchemyUnitOfWork(SessionFactory)
    password_hasher = Argon2PasswordHasher()

    access_token_service = JWTAccessTokenService(
        secret=settings.auth_jwt_secret,
        algorithm=settings.auth_jwt_algorithm,
        ttl_minutes=settings.access_token_ttl_minutes,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )

    refresh_token_service = SecureRefreshTokenService()

    return LoginUser(
        unit_of_work=unit_of_work,
        password_hasher=password_hasher,
        access_token_service=access_token_service,
        refresh_token_service=refresh_token_service,
        refresh_token_ttl_days=settings.refresh_token_ttl_days,
        access_token_ttl_minutes=settings.access_token_ttl_minutes,
    )


def get_refresh_session_use_case() -> RefreshSession:
    settings = get_settings()

    unit_of_work = SQLAlchemyUnitOfWork(SessionFactory)

    access_token_service = JWTAccessTokenService(
        secret=settings.auth_jwt_secret,
        algorithm=settings.auth_jwt_algorithm,
        ttl_minutes=settings.access_token_ttl_minutes,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )

    refresh_token_service = SecureRefreshTokenService()

    return RefreshSession(
        unit_of_work=unit_of_work,
        access_token_service=access_token_service,
        refresh_token_service=refresh_token_service,
        refresh_token_ttl_days=settings.refresh_token_ttl_days,
        access_token_ttl_minutes=settings.access_token_ttl_minutes,
    )


def get_logout_user_use_case() -> LogoutUser:
    return LogoutUser(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
        refresh_token_service=SecureRefreshTokenService(),
    )


def get_active_membership_use_case() -> GetActiveMembership:
    return GetActiveMembership(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_check_permission_use_case() -> CheckPermission:
    return CheckPermission(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_create_tenant_use_case() -> CreateTenant:
    return CreateTenant(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_list_user_tenants_use_case() -> ListUserTenants:
    return ListUserTenants(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )
