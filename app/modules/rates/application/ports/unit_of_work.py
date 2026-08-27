from types import TracebackType
from typing import Protocol

from app.modules.rates.application.ports.rate_quote_repository import (
    RateQuoteRepository,
)
from app.modules.rates.infrastructure.models.rate_quote import RateQuote
from app.modules.shipments.application.ports.shipment_repository import (
    ShipmentRepository,
)


class UnitOfWork(Protocol):
    @property
    def rate_quotes(self) -> RateQuoteRepository: ...

    @property
    def shipments(self) -> ShipmentRepository: ...

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
        rate_quote: RateQuote,
    ) -> None: ...
