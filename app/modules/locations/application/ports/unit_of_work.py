from types import TracebackType
from typing import Protocol

from app.modules.locations.application.ports.location_repository import (
    LocationRepository,
)
from app.modules.locations.infrastructure.models.location import Location


class UnitOfWork(Protocol):
    @property
    def locations(self) -> LocationRepository: ...

    async def __aenter__(self) -> "UnitOfWork": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def flush(self) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def refresh(
        self,
        location: Location,
    ) -> None: ...
