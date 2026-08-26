from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.identity.api.auth_dependencies import get_current_user
from app.modules.identity.api.dependencies import (
    get_login_user_use_case,
    get_logout_user_use_case,
    get_refresh_session_use_case,
    get_register_user_use_case,
)
from app.modules.identity.api.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterUserRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.identity.application.exceptions import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
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
from app.modules.identity.application.use_cases.register_user import (
    RegisterUser,
    RegisterUserCommand,
)
from app.modules.identity.infrastructure.models.user import User

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    request: RegisterUserRequest,
    use_case: Annotated[
        RegisterUser,
        Depends(get_register_user_use_case),
    ],
) -> UserResponse:
    try:
        user = await use_case.execute(
            RegisterUserCommand(
                email=str(request.email),
                password=request.password,
                first_name=request.first_name,
                last_name=request.last_name,
            )
        )
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from exc

    return UserResponse.model_validate(user)


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
