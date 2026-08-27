from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.modules.rates.application.exceptions import (
    RateQuoteShipmentNotFoundError,
)
from app.modules.rates.application.ports.unit_of_work import UnitOfWork
from app.modules.rates.domain.enums import RateQuoteStatus
from app.modules.rates.infrastructure.models.rate_quote import RateQuote


@dataclass(frozen=True, slots=True)
class CreateRateQuoteCommand:
    tenant_id: UUID
    shipment_id: UUID
    currency: str
    base_amount: Decimal
    surcharge_amount: Decimal
    expires_at: datetime | None = None


class CreateRateQuote:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: CreateRateQuoteCommand,
    ) -> RateQuote:
        currency = command.currency.strip().upper()
        total_amount = command.base_amount + command.surcharge_amount

        async with self._unit_of_work as uow:
            shipment = await uow.shipments.get_by_id_and_tenant(
                command.shipment_id,
                command.tenant_id,
            )

            if shipment is None:
                raise RateQuoteShipmentNotFoundError

            rate_quote = RateQuote(
                tenant_id=command.tenant_id,
                shipment_id=command.shipment_id,
                currency=currency,
                base_amount=command.base_amount,
                surcharge_amount=command.surcharge_amount,
                total_amount=total_amount,
                status=RateQuoteStatus.DRAFT,
                expires_at=command.expires_at,
            )

            uow.rate_quotes.add(rate_quote)

            await uow.flush()
            await uow.commit()
            await uow.refresh(rate_quote)

            return rate_quote
