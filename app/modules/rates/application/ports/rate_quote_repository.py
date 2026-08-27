from typing import Protocol
from uuid import UUID

from app.modules.rates.infrastructure.models.rate_quote import RateQuote


class RateQuoteRepository(Protocol):
    async def get_by_id_and_tenant(
        self,
        rate_quote_id: UUID,
        tenant_id: UUID,
    ) -> RateQuote | None: ...

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[RateQuote]: ...

    async def list_by_shipment(
        self,
        shipment_id: UUID,
        tenant_id: UUID,
    ) -> list[RateQuote]: ...

    def add(
        self,
        rate_quote: RateQuote,
    ) -> None: ...
