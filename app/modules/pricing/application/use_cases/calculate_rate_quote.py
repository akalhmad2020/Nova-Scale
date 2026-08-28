from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP
from uuid import UUID

from app.modules.pricing.application.exceptions import (
    PricingRuleInactiveError,
    PricingRuleNotEffectiveError,
    PricingRuleNotFoundError,
    PricingRuleServiceMismatchError,
    PricingShipmentNotFoundError,
)
from app.modules.pricing.application.ports.unit_of_work import UnitOfWork
from app.modules.pricing.domain.calculator import (
    MONEY_QUANTUM,
    calculate_total_amount,
    calculate_weight_charge,
)
from app.modules.pricing.domain.enums import PricingRuleStatus
from app.modules.rates.domain.enums import RateQuoteStatus
from app.modules.rates.infrastructure.models.rate_quote import RateQuote


@dataclass(frozen=True, slots=True)
class CalculateRateQuoteCommand:
    tenant_id: UUID
    shipment_id: UUID
    pricing_rule_id: UUID


class CalculateRateQuote:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: CalculateRateQuoteCommand,
    ) -> RateQuote:
        async with self._unit_of_work as uow:
            shipment = await uow.shipments.get_by_id_and_tenant(
                command.shipment_id,
                command.tenant_id,
            )

            if shipment is None:
                raise PricingShipmentNotFoundError

            pricing_rule = await uow.pricing_rules.get_by_id_and_tenant(
                command.pricing_rule_id,
                command.tenant_id,
            )

            if pricing_rule is None:
                raise PricingRuleNotFoundError

            if pricing_rule.status != PricingRuleStatus.ACTIVE:
                raise PricingRuleInactiveError

            if pricing_rule.service_type != shipment.service_type:
                raise PricingRuleServiceMismatchError

            now = datetime.now(UTC)

            if pricing_rule.valid_from is not None and now < pricing_rule.valid_from:
                raise PricingRuleNotEffectiveError

            if pricing_rule.valid_until is not None and now >= pricing_rule.valid_until:
                raise PricingRuleNotEffectiveError

            weight_charge = calculate_weight_charge(
                weight=shipment.weight,
                weight_unit=shipment.weight_unit,
                price_per_kg=pricing_rule.price_per_kg,
            )

            surcharge_amount = (weight_charge + pricing_rule.surcharge_amount).quantize(
                MONEY_QUANTUM,
                rounding=ROUND_HALF_UP,
            )

            base_amount = pricing_rule.base_amount.quantize(
                MONEY_QUANTUM,
                rounding=ROUND_HALF_UP,
            )

            total_amount = calculate_total_amount(
                base_amount=base_amount,
                surcharge_amount=surcharge_amount,
            )

            rate_quote = RateQuote(
                tenant_id=command.tenant_id,
                shipment_id=shipment.id,
                currency=pricing_rule.currency,
                base_amount=base_amount,
                surcharge_amount=surcharge_amount,
                total_amount=total_amount,
                status=RateQuoteStatus.DRAFT,
                expires_at=pricing_rule.valid_until,
            )

            uow.rate_quotes.add(rate_quote)

            await uow.flush()
            await uow.commit()
            await uow.refresh(rate_quote)

            return rate_quote
