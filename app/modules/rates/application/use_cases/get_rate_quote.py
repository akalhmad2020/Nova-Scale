from dataclasses import dataclass
from uuid import UUID

from app.modules.rates.application.exceptions import RateQuoteNotFoundError
from app.modules.rates.application.ports.unit_of_work import UnitOfWork
from app.modules.rates.infrastructure.models.rate_quote import RateQuote


@dataclass(frozen=True, slots=True)
class GetRateQuoteQuery:
    tenant_id: UUID
    rate_quote_id: UUID


class GetRateQuote:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: GetRateQuoteQuery,
    ) -> RateQuote:
        async with self._unit_of_work as uow:
            rate_quote = await uow.rate_quotes.get_by_id_and_tenant(
                query.rate_quote_id,
                query.tenant_id,
            )

            if rate_quote is None:
                raise RateQuoteNotFoundError

            return rate_quote
