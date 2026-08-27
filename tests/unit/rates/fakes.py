from types import TracebackType
from uuid import UUID

from app.modules.rates.infrastructure.models.rate_quote import RateQuote
from app.modules.shipments.infrastructure.models.shipment import Shipment


class FakeRateQuoteRepository:
    def __init__(self) -> None:
        self.items: list[RateQuote] = []

    async def get_by_id_and_tenant(
        self,
        rate_quote_id: UUID,
        tenant_id: UUID,
    ) -> RateQuote | None:
        return next(
            (
                rate_quote
                for rate_quote in self.items
                if rate_quote.id == rate_quote_id and rate_quote.tenant_id == tenant_id
            ),
            None,
        )

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[RateQuote]:
        return [rate_quote for rate_quote in self.items if rate_quote.tenant_id == tenant_id]

    async def list_by_shipment(
        self,
        shipment_id: UUID,
        tenant_id: UUID,
    ) -> list[RateQuote]:
        return [
            rate_quote
            for rate_quote in self.items
            if rate_quote.shipment_id == shipment_id and rate_quote.tenant_id == tenant_id
        ]

    def add(
        self,
        rate_quote: RateQuote,
    ) -> None:
        self.items.append(rate_quote)


class FakeShipmentRepository:
    def __init__(self) -> None:
        self.items: list[Shipment] = []

    async def get_by_id_and_tenant(
        self,
        shipment_id: UUID,
        tenant_id: UUID,
    ) -> Shipment | None:
        return next(
            (
                shipment
                for shipment in self.items
                if shipment.id == shipment_id
                and shipment.tenant_id == tenant_id
                and shipment.deleted_at is None
            ),
            None,
        )

    async def get_by_tracking_number_and_tenant(
        self,
        tracking_number: str,
        tenant_id: UUID,
    ) -> Shipment | None:
        return next(
            (
                shipment
                for shipment in self.items
                if shipment.tracking_number == tracking_number
                and shipment.tenant_id == tenant_id
                and shipment.deleted_at is None
            ),
            None,
        )

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[Shipment]:
        return [
            shipment
            for shipment in self.items
            if shipment.tenant_id == tenant_id and shipment.deleted_at is None
        ]

    def add(
        self,
        shipment: Shipment,
    ) -> None:
        self.items.append(shipment)


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.rate_quotes = FakeRateQuoteRepository()
        self.shipments = FakeShipmentRepository()

        self.flushed = False
        self.committed = False
        self.rolled_back = False
        self.refreshed = False

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def flush(self) -> None:
        self.flushed = True

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def refresh(
        self,
        rate_quote: RateQuote,
    ) -> None:
        self.refreshed = True
