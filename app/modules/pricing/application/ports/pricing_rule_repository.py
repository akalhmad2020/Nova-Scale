from typing import Protocol
from uuid import UUID

from app.modules.pricing.infrastructure.models.pricing_rule import PricingRule


class PricingRuleRepository(Protocol):
    async def get_by_id_and_tenant(
        self,
        pricing_rule_id: UUID,
        tenant_id: UUID,
    ) -> PricingRule | None: ...

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[PricingRule]: ...

    def add(
        self,
        pricing_rule: PricingRule,
    ) -> None: ...
