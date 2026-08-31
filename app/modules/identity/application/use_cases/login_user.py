from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.modules.identity.application.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
)
from app.modules.identity.application.ports.access_token_service import (
    AccessTokenService,
)
from app.modules.identity.application.ports.password_hasher import PasswordHasher
from app.modules.identity.application.ports.refresh_token_service import (
    RefreshTokenService,
)
from app.modules.identity.application.ports.unit_of_work import UnitOfWork
from app.modules.identity.infrastructure.models.auth_session import AuthSession


@dataclass(frozen=True, slots=True)
class LoginUserCommand:
    email: str
    password: str


@dataclass(frozen=True, slots=True)
class LoginResult:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class LoginUser:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        password_hasher: PasswordHasher,
        access_token_service: AccessTokenService,
        refresh_token_service: RefreshTokenService,
        refresh_token_ttl_days: int,
        access_token_ttl_minutes: int,
        max_failed_attempts: int,
        lockout_minutes: int,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._password_hasher = password_hasher
        self._access_token_service = access_token_service
        self._refresh_token_service = refresh_token_service
        self._refresh_token_ttl_days = refresh_token_ttl_days
        self._access_token_ttl_minutes = access_token_ttl_minutes
        self._max_failed_attempts = max_failed_attempts
        self._lockout_minutes = lockout_minutes

    async def execute(
        self,
        command: LoginUserCommand,
    ) -> LoginResult:
        email = command.email.strip().lower()

        async with self._unit_of_work as uow:
            user = await uow.users.get_by_email_for_update(email)

            if user is None:
                raise InvalidCredentialsError

            if not user.is_active:
                raise InactiveUserError

            now = datetime.now(UTC)

            if user.locked_until is not None and user.locked_until > now:
                raise InvalidCredentialsError

            if user.locked_until is not None:
                user.failed_login_attempts = 0
                user.locked_until = None

            if not self._password_hasher.verify(
                command.password,
                user.password_hash,
            ):
                user.failed_login_attempts += 1

                if user.failed_login_attempts >= self._max_failed_attempts:
                    user.locked_until = now + timedelta(
                        minutes=self._lockout_minutes,
                    )

                await uow.commit()

                raise InvalidCredentialsError

            user.failed_login_attempts = 0
            user.locked_until = None

            if self._password_hasher.needs_rehash(user.password_hash):
                user.password_hash = self._password_hasher.hash(command.password)

            access_token = self._access_token_service.create(user.id)

            refresh_token = self._refresh_token_service.generate()
            refresh_token_hash = self._refresh_token_service.hash(refresh_token)

            auth_session = AuthSession(
                user_id=user.id,
                refresh_token_hash=refresh_token_hash,
                expires_at=now
                + timedelta(
                    days=self._refresh_token_ttl_days,
                ),
            )

            uow.auth_sessions.add(auth_session)

            await uow.flush()
            await uow.commit()

            return LoginResult(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=self._access_token_ttl_minutes * 60,
            )
