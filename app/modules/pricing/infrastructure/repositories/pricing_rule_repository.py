from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.pricing.infrastructure.models.pricing_rule import PricingRule


class PricingRuleRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def get_by_id_and_tenant(
        self,
        pricing_rule_id: UUID,
        tenant_id: UUID,
    ) -> PricingRule | None:
        statement = select(PricingRule).where(
            PricingRule.id == pricing_rule_id,
            PricingRule.tenant_id == tenant_id,
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[PricingRule]:
        statement = (
            select(PricingRule)
            .where(
                PricingRule.tenant_id == tenant_id,
            )
            .order_by(
                PricingRule.created_at.desc(),
            )
        )

        result = await self._session.execute(statement)

        return list(result.scalars().all())

    def add(
        self,
        pricing_rule: PricingRule,
    ) -> None:
        self._session.add(pricing_rule)
