from dataclasses import dataclass
from uuid import UUID

from app.modules.rates.application.exceptions import (
    InvalidRateQuoteStatusTransitionError,
    RateQuoteNotFoundError,
)
from app.modules.rates.application.ports.unit_of_work import UnitOfWork
from app.modules.rates.domain.enums import RateQuoteStatus
from app.modules.rates.domain.lifecycle import (
    can_transition_rate_quote_status,
)
from app.modules.rates.infrastructure.models.rate_quote import RateQuote


@dataclass(frozen=True, slots=True)
class TransitionRateQuoteStatusCommand:
    tenant_id: UUID
    rate_quote_id: UUID
    status: RateQuoteStatus


class TransitionRateQuoteStatus:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: TransitionRateQuoteStatusCommand,
    ) -> RateQuote:
        async with self._unit_of_work as uow:
            rate_quote = await uow.rate_quotes.get_by_id_and_tenant(
                command.rate_quote_id,
                command.tenant_id,
            )

            if rate_quote is None:
                raise RateQuoteNotFoundError

            if not can_transition_rate_quote_status(
                rate_quote.status,
                command.status,
            ):
                raise InvalidRateQuoteStatusTransitionError

            rate_quote.status = command.status

            await uow.flush()
            await uow.commit()
            await uow.refresh(rate_quote)

            return rate_quote
