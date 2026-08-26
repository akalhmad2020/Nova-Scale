from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.modules.identity.application.exceptions import (
    InvalidRefreshTokenError,
)
from app.modules.identity.application.ports.access_token_service import (
    AccessTokenService,
)
from app.modules.identity.application.ports.refresh_token_service import (
    RefreshTokenService,
)
from app.modules.identity.application.ports.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class RefreshSessionCommand:
    refresh_token: str


@dataclass(frozen=True, slots=True)
class RefreshSessionResult:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class RefreshSession:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        access_token_service: AccessTokenService,
        refresh_token_service: RefreshTokenService,
        refresh_token_ttl_days: int,
        access_token_ttl_minutes: int,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._access_token_service = access_token_service
        self._refresh_token_service = refresh_token_service
        self._refresh_token_ttl_days = refresh_token_ttl_days
        self._access_token_ttl_minutes = access_token_ttl_minutes

    async def execute(
        self,
        command: RefreshSessionCommand,
    ) -> RefreshSessionResult:
        refresh_token_hash = self._refresh_token_service.hash(command.refresh_token)

        async with self._unit_of_work as uow:
            auth_session = await uow.auth_sessions.get_by_refresh_token_hash_for_update(
                refresh_token_hash
            )

            if auth_session is None:
                raise InvalidRefreshTokenError

            now = datetime.now(UTC)

            if auth_session.revoked_at is not None:
                raise InvalidRefreshTokenError

            if auth_session.expires_at <= now:
                raise InvalidRefreshTokenError

            user = await uow.users.get_by_id(auth_session.user_id)

            if user is None or not user.is_active:
                raise InvalidRefreshTokenError

            new_access_token = self._access_token_service.create(user.id)

            new_refresh_token = self._refresh_token_service.generate()

            auth_session.refresh_token_hash = self._refresh_token_service.hash(new_refresh_token)

            auth_session.expires_at = now + timedelta(days=self._refresh_token_ttl_days)

            await uow.flush()
            await uow.commit()

            return RefreshSessionResult(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                token_type="bearer",
                expires_in=self._access_token_ttl_minutes * 60,
            )
