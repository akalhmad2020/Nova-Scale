from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError

from app.modules.identity.application.exceptions import (
    EmailAlreadyRegisteredError,
)
from app.modules.identity.application.ports.password_hasher import PasswordHasher
from app.modules.identity.application.ports.unit_of_work import UnitOfWork
from app.modules.identity.infrastructure.models.user import User


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    email: str
    password: str
    first_name: str
    last_name: str


class RegisterUser:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        password_hasher: PasswordHasher,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._password_hasher = password_hasher

    async def execute(self, command: RegisterUserCommand) -> User:
        email = self._normalize_email(command.email)

        async with self._unit_of_work as uow:
            if await uow.users.email_exists(email):
                raise EmailAlreadyRegisteredError

            password_hash = self._password_hasher.hash(command.password)

            user = User(
                email=email,
                password_hash=password_hash,
                first_name=command.first_name.strip(),
                last_name=command.last_name.strip(),
            )

            uow.users.add(user)

            try:
                await uow.flush()
            except IntegrityError as exc:
                raise EmailAlreadyRegisteredError from exc

            await uow.commit()

            return user

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()
