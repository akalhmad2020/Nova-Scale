from dataclasses import dataclass
from uuid import UUID

from app.modules.pricing.application.ports.unit_of_work import UnitOfWork
from app.modules.pricing.infrastructure.models.pricing_rule import PricingRule


@dataclass(frozen=True, slots=True)
class ListPricingRulesQuery:
    tenant_id: UUID


class ListPricingRules:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: ListPricingRulesQuery,
    ) -> list[PricingRule]:
        async with self._unit_of_work as uow:
            return await uow.pricing_rules.list_by_tenant(
                query.tenant_id,
            )
