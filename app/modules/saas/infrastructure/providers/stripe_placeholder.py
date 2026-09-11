from uuid import UUID

from app.modules.saas.application.exceptions import (
    SubscriptionProviderUnavailableError,
)
from app.modules.saas.application.ports.subscription_provider import (
    SubscriptionActivation,
)
from app.modules.saas.domain.enums import PlanCode


class StripeSubscriptionProviderPlaceholder:
    """Explicit boundary for the future Stripe adapter.

    Keeping this adapter in place means BILLING_PROVIDER=stripe fails closed
    instead of silently granting a paid plan before Stripe is implemented.
    """

    @property
    def name(self) -> str:
        return "stripe"

    async def activate_plan(
        self,
        *,
        tenant_id: UUID,
        current_plan: PlanCode,
        requested_plan: PlanCode,
    ) -> SubscriptionActivation:
        del tenant_id, current_plan, requested_plan
        raise SubscriptionProviderUnavailableError(
            "Stripe billing is configured but the Stripe adapter is not installed yet."
        )
