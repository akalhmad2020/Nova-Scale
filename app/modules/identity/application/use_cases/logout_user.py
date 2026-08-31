from dataclasses import dataclass
from datetime import UTC, datetime

from app.modules.identity.application.exceptions import (
    InvalidRefreshTokenError,
)
from app.modules.identity.application.ports.refresh_token_service import (
    RefreshTokenService,
)
from app.modules.identity.application.ports.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class LogoutUserCommand:
    refresh_token: str


class LogoutUser:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        refresh_token_service: RefreshTokenService,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._refresh_token_service = refresh_token_service

    async def execute(
        self,
        command: LogoutUserCommand,
    ) -> None:
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

            auth_session.revoked_at = now

            await uow.flush()
            await uow.commit()
