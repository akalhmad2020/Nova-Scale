from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.modules.saas.domain.enums import PlanCode, SubscriptionStatus


@dataclass(frozen=True, slots=True)
class SubscriptionActivation:
    plan_code: PlanCode
    status: SubscriptionStatus
    provider: str
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    provider_customer_id: str | None = None
    provider_subscription_id: str | None = None


class SubscriptionProvider(Protocol):
    @property
    def name(self) -> str: ...

    async def activate_plan(
        self,
        *,
        tenant_id: UUID,
        current_plan: PlanCode,
        requested_plan: PlanCode,
    ) -> SubscriptionActivation: ...
