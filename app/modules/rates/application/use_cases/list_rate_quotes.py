from dataclasses import dataclass
from uuid import UUID

from app.modules.rates.application.exceptions import (
    RateQuoteShipmentNotFoundError,
)
from app.modules.rates.application.ports.unit_of_work import UnitOfWork
from app.modules.rates.infrastructure.models.rate_quote import RateQuote


@dataclass(frozen=True, slots=True)
class ListRateQuotesQuery:
    tenant_id: UUID
    shipment_id: UUID


class ListRateQuotes:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: ListRateQuotesQuery,
    ) -> list[RateQuote]:
        async with self._unit_of_work as uow:
            shipment = await uow.shipments.get_by_id_and_tenant(
                query.shipment_id,
                query.tenant_id,
            )

            if shipment is None:
                raise RateQuoteShipmentNotFoundError

            return await uow.rate_quotes.list_by_shipment(
                query.shipment_id,
                query.tenant_id,
            )
