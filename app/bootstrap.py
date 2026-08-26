import asyncio

from app.core.database import SessionFactory
from app.modules.identity.application.use_cases.bootstrap_authorization import (
    BootstrapAuthorization,
)
from app.modules.identity.infrastructure.unit_of_work import SQLAlchemyUnitOfWork


async def bootstrap() -> None:
    authorization = BootstrapAuthorization(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )

    await authorization.execute()


def main() -> None:
    asyncio.run(bootstrap())


if __name__ == "__main__":
    main()
