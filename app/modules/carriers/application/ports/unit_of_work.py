from types import TracebackType
from typing import Protocol

from app.modules.carriers.application.ports.carrier_repository import (
    CarrierRepository,
)
from app.modules.carriers.application.ports.carrier_service_repository import (
    CarrierServiceRepository,
)
from app.modules.carriers.infrastructure.models.carrier import Carrier
from app.modules.carriers.infrastructure.models.carrier_service import (
    CarrierService,
)


class UnitOfWork(Protocol):
    @property
    def carriers(self) -> CarrierRepository: ...

    @property
    def carrier_services(self) -> CarrierServiceRepository: ...

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
        model: Carrier | CarrierService,
    ) -> None: ...
