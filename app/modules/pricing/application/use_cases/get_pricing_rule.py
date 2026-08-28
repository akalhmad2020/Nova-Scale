from dataclasses import dataclass
from uuid import UUID

from app.modules.pricing.application.exceptions import PricingRuleNotFoundError
from app.modules.pricing.application.ports.unit_of_work import UnitOfWork
from app.modules.pricing.infrastructure.models.pricing_rule import PricingRule


@dataclass(frozen=True, slots=True)
class GetPricingRuleQuery:
    tenant_id: UUID
    pricing_rule_id: UUID


class GetPricingRule:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: GetPricingRuleQuery,
    ) -> PricingRule:
        async with self._unit_of_work as uow:
            pricing_rule = await uow.pricing_rules.get_by_id_and_tenant(
                query.pricing_rule_id,
                query.tenant_id,
            )

            if pricing_rule is None:
                raise PricingRuleNotFoundError

            return pricing_rule
