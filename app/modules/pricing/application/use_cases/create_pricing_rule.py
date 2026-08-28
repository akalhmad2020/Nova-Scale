from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.modules.pricing.application.exceptions import (
    PricingRuleInvalidValidityRangeError,
)
from app.modules.pricing.application.ports.unit_of_work import UnitOfWork
from app.modules.pricing.domain.enums import PricingRuleStatus
from app.modules.pricing.infrastructure.models.pricing_rule import PricingRule
from app.modules.shipments.domain.enums import ServiceType


@dataclass(frozen=True, slots=True)
class CreatePricingRuleCommand:
    tenant_id: UUID
    name: str
    service_type: ServiceType
    currency: str
    base_amount: Decimal
    price_per_kg: Decimal
    surcharge_amount: Decimal
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class CreatePricingRule:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: CreatePricingRuleCommand,
    ) -> PricingRule:
        name = command.name.strip()
        currency = command.currency.strip().upper()

        if (
            command.valid_from is not None
            and command.valid_until is not None
            and command.valid_until <= command.valid_from
        ):
            raise PricingRuleInvalidValidityRangeError

        async with self._unit_of_work as uow:
            pricing_rule = PricingRule(
                tenant_id=command.tenant_id,
                name=name,
                service_type=command.service_type,
                currency=currency,
                base_amount=command.base_amount,
                price_per_kg=command.price_per_kg,
                surcharge_amount=command.surcharge_amount,
                status=PricingRuleStatus.ACTIVE,
                valid_from=command.valid_from,
                valid_until=command.valid_until,
            )

            uow.pricing_rules.add(pricing_rule)

            await uow.flush()
            await uow.commit()
            await uow.refresh(pricing_rule)

            return pricing_rule
