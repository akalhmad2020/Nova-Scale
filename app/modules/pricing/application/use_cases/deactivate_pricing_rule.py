from dataclasses import dataclass
from uuid import UUID

from app.modules.pricing.application.exceptions import (
    PricingRuleAlreadyInactiveError,
    PricingRuleNotFoundError,
)
from app.modules.pricing.application.ports.unit_of_work import UnitOfWork
from app.modules.pricing.domain.enums import PricingRuleStatus
from app.modules.pricing.infrastructure.models.pricing_rule import PricingRule


@dataclass(frozen=True, slots=True)
class DeactivatePricingRuleCommand:
    tenant_id: UUID
    pricing_rule_id: UUID


class DeactivatePricingRule:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: DeactivatePricingRuleCommand,
    ) -> PricingRule:
        async with self._unit_of_work as uow:
            pricing_rule = await uow.pricing_rules.get_by_id_and_tenant(
                command.pricing_rule_id,
                command.tenant_id,
            )

            if pricing_rule is None:
                raise PricingRuleNotFoundError

            if pricing_rule.status == PricingRuleStatus.INACTIVE:
                raise PricingRuleAlreadyInactiveError

            pricing_rule.status = PricingRuleStatus.INACTIVE

            await uow.flush()
            await uow.commit()
            await uow.refresh(pricing_rule)

            return pricing_rule
