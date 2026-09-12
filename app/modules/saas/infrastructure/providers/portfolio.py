from uuid import UUID

from app.modules.saas.application.ports.subscription_provider import (
    SubscriptionActivation,
)
from app.modules.saas.domain.enums import PlanCode, SubscriptionStatus


class PortfolioSubscriptionProvider:
    """Instant plan activation used by the public portfolio/demo environment.

    Stripe can later implement the same SubscriptionProvider port and replace
    this adapter without changing the subscription use case or entitlements.
    """

    @property
    def name(self) -> str:
        return "portfolio"

    async def activate_plan(
        self,
        *,
        tenant_id: UUID,
        current_plan: PlanCode,
        requested_plan: PlanCode,
    ) -> SubscriptionActivation:
        del tenant_id, current_plan

        return SubscriptionActivation(
            plan_code=requested_plan,
            status=SubscriptionStatus.ACTIVE,
            provider=self.name,
        )
