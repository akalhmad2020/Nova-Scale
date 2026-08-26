from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.database import SessionFactory
from app.modules.identity.api.dependencies import (
    get_active_membership_use_case,
    get_check_permission_use_case,
)
from app.modules.identity.application.exceptions import (
    InactiveMembershipError,
    InactiveTenantError,
    MembershipNotFoundError,
    PermissionDeniedError,
    TenantNotFoundError,
)
from app.modules.identity.application.use_cases.check_permission import (
    CheckPermission,
    CheckPermissionQuery,
)
from app.modules.identity.application.use_cases.get_active_membership import (
    GetActiveMembership,
    GetActiveMembershipQuery,
)
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.user import User
from app.modules.identity.infrastructure.repositories.user_repository import (
    UserRepository,
)
from app.modules.identity.infrastructure.security.access_token_service import (
    ExpiredAccessTokenError,
    InvalidAccessTokenError,
    JWTAccessTokenService,
)

bearer_scheme = HTTPBearer(
    auto_error=False,
)


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_settings()

    access_token_service = JWTAccessTokenService(
        secret=settings.auth_jwt_secret,
        algorithm=settings.auth_jwt_algorithm,
        ttl_minutes=settings.access_token_ttl_minutes,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )

    try:
        claims = access_token_service.decode(credentials.credentials)
    except (InvalidAccessTokenError, ExpiredAccessTokenError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    async with SessionFactory() as session:
        repository = UserRepository(session)

        user = await repository.get_by_id(claims.subject)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_membership(
    tenant_id: UUID,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    use_case: Annotated[
        GetActiveMembership,
        Depends(get_active_membership_use_case),
    ],
) -> Membership:
    try:
        return await use_case.execute(
            GetActiveMembershipQuery(
                user_id=current_user.id,
                tenant_id=tenant_id,
            )
        )
    except TenantNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        ) from exc
    except (
        MembershipNotFoundError,
        InactiveMembershipError,
        InactiveTenantError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this tenant is forbidden",
        ) from exc


def require_permission(
    permission_code: str,
) -> Callable[..., object]:
    async def dependency(
        membership: Annotated[
            Membership,
            Depends(get_current_membership),
        ],
        use_case: Annotated[
            CheckPermission,
            Depends(get_check_permission_use_case),
        ],
    ) -> Membership:
        try:
            await use_case.execute(
                CheckPermissionQuery(
                    role_id=membership.role_id,
                    permission_code=permission_code,
                )
            )
        except PermissionDeniedError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            ) from exc

        return membership

    return dependency
