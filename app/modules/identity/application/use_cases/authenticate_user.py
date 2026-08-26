from dataclasses import dataclass

from app.modules.identity.application.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
)
from app.modules.identity.application.ports.password_hasher import PasswordHasher
from app.modules.identity.application.ports.unit_of_work import UnitOfWork
from app.modules.identity.infrastructure.models.user import User


@dataclass(frozen=True, slots=True)
class AuthenticateUserCommand:
    email: str
    password: str


class AuthenticateUser:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        password_hasher: PasswordHasher,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._password_hasher = password_hasher

    async def execute(self, command: AuthenticateUserCommand) -> User:
        email = self._normalize_email(command.email)

        async with self._unit_of_work as uow:
            user = await uow.users.get_by_email(email)

            if user is None:
                raise InvalidCredentialsError

            if not user.is_active:
                raise InactiveUserError

            if not self._password_hasher.verify(
                command.password,
                user.password_hash,
            ):
                raise InvalidCredentialsError

            return user

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()
