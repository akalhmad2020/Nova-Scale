from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.identity.api.auth_dependencies import get_current_user
from app.modules.identity.api.dependencies import (
    get_login_user_use_case,
    get_logout_user_use_case,
    get_refresh_session_use_case,
    get_register_company_use_case,
)
from app.modules.identity.api.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterCompanyRequest,
    RegisterCompanyResponse,
    TokenResponse,
    UserResponse,
)
from app.modules.identity.application.exceptions import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    TenantSlugAlreadyExistsError,
)
from app.modules.identity.application.use_cases.login_user import (
    LoginUser,
    LoginUserCommand,
)
from app.modules.identity.application.use_cases.logout_user import (
    LogoutUser,
    LogoutUserCommand,
)
from app.modules.identity.application.use_cases.refresh_session import (
    RefreshSession,
    RefreshSessionCommand,
)
from app.modules.identity.application.use_cases.register_company import (
    RegisterCompany,
    RegisterCompanyCommand,
)
from app.modules.identity.infrastructure.models.user import User
from app.modules.saas.application.exceptions import SelfServicePlanUnavailableError
from app.modules.saas.domain.enums import PlanCode

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


class RegisterCompanyWithPlanRequest(RegisterCompanyRequest):
    plan_code: PlanCode = PlanCode.STARTER


@router.post(
    "/register",
    response_model=RegisterCompanyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_company(
    request: RegisterCompanyWithPlanRequest,
    use_case: Annotated[
        RegisterCompany,
        Depends(get_register_company_use_case),
    ],
) -> RegisterCompanyResponse:
    try:
        result = await use_case.execute(
            RegisterCompanyCommand(
                email=str(request.email),
                password=request.password,
                first_name=request.first_name,
                last_name=request.last_name,
                company_name=request.company_name,
                company_slug=request.company_slug,
                plan_code=request.plan_code,
            )
        )
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from exc
    except TenantSlugAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tenant slug already exists",
        ) from exc
    except SelfServicePlanUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This plan is not available for self-service signup",
        ) from exc

    return RegisterCompanyResponse(
        user_id=result.user_id,
        tenant_id=result.tenant_id,
        membership_id=result.membership_id,
        email=result.email,
        first_name=result.first_name,
        last_name=result.last_name,
        company_name=result.company_name,
        company_slug=result.company_slug,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def login_user(
    request: LoginRequest,
    use_case: Annotated[
        LoginUser,
        Depends(get_login_user_use_case),
    ],
) -> TokenResponse:
    try:
        result = await use_case.execute(
            LoginUserCommand(
                email=str(request.email),
                password=request.password,
            )
        )
    except (InvalidCredentialsError, InactiveUserError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        expires_in=result.expires_in,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh_session(
    request: RefreshTokenRequest,
    use_case: Annotated[
        RefreshSession,
        Depends(get_refresh_session_use_case),
    ],
) -> TokenResponse:
    try:
        result = await use_case.execute(
            RefreshSessionCommand(
                refresh_token=request.refresh_token,
            )
        )
    except InvalidRefreshTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        expires_in=result.expires_in,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout_user(
    request: LogoutRequest,
    use_case: Annotated[
        LogoutUser,
        Depends(get_logout_user_use_case),
    ],
) -> None:
    try:
        await use_case.execute(
            LogoutUserCommand(
                refresh_token=request.refresh_token,
            )
        )
    except InvalidRefreshTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_me(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
) -> UserResponse:
    return UserResponse.model_validate(current_user)
