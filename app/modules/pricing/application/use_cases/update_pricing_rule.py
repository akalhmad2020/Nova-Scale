from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.modules.pricing.application.exceptions import (
    PricingRuleInvalidValidityRangeError,
    PricingRuleNotFoundError,
)
from app.modules.pricing.application.ports.unit_of_work import UnitOfWork
from app.modules.pricing.infrastructure.models.pricing_rule import PricingRule
from app.modules.shipments.domain.enums import ServiceType


class UnsetType:
    __slots__ = ()


UNSET = UnsetType()


@dataclass(frozen=True, slots=True)
class UpdatePricingRuleCommand:
    tenant_id: UUID
    pricing_rule_id: UUID

    name: str | None = None
    service_type: ServiceType | None = None
    currency: str | None = None

    base_amount: Decimal | None = None
    price_per_kg: Decimal | None = None
    surcharge_amount: Decimal | None = None

    valid_from: datetime | None | UnsetType = UNSET
    valid_until: datetime | None | UnsetType = UNSET


class UpdatePricingRule:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: UpdatePricingRuleCommand,
    ) -> PricingRule:
        async with self._unit_of_work as uow:
            pricing_rule = await uow.pricing_rules.get_by_id_and_tenant(
                command.pricing_rule_id,
                command.tenant_id,
            )

            if pricing_rule is None:
                raise PricingRuleNotFoundError

            valid_from = (
                pricing_rule.valid_from
                if isinstance(command.valid_from, UnsetType)
                else command.valid_from
            )

            valid_until = (
                pricing_rule.valid_until
                if isinstance(command.valid_until, UnsetType)
                else command.valid_until
            )

            if valid_from is not None and valid_until is not None and valid_until <= valid_from:
                raise PricingRuleInvalidValidityRangeError

            if command.name is not None:
                pricing_rule.name = command.name.strip()

            if command.service_type is not None:
                pricing_rule.service_type = command.service_type

            if command.currency is not None:
                pricing_rule.currency = command.currency.strip().upper()

            if command.base_amount is not None:
                pricing_rule.base_amount = command.base_amount

            if command.price_per_kg is not None:
                pricing_rule.price_per_kg = command.price_per_kg

            if command.surcharge_amount is not None:
                pricing_rule.surcharge_amount = command.surcharge_amount

            if not isinstance(command.valid_from, UnsetType):
                pricing_rule.valid_from = command.valid_from

            if not isinstance(command.valid_until, UnsetType):
                pricing_rule.valid_until = command.valid_until

            await uow.flush()
            await uow.commit()
            await uow.refresh(pricing_rule)

            return pricing_rule
