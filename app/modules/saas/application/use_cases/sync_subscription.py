from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.saas.application.ports.unit_of_work import SubscriptionUnitOfWork
from app.modules.saas.domain.enums import PlanCode, SubscriptionStatus
from app.modules.saas.infrastructure.models.subscription import TenantSubscription


@dataclass(frozen=True, slots=True)
class SyncSubscriptionCommand:
    tenant_id: UUID
    plan_code: PlanCode
    status: SubscriptionStatus
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    provider: str | None = None
    provider_customer_id: str | None = None
    provider_subscription_id: str | None = None


class SyncSubscription:
    """Idempotently applies subscription state supplied by a trusted billing integration."""

    def __init__(self, unit_of_work: SubscriptionUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, command: SyncSubscriptionCommand) -> TenantSubscription:
        async with self._unit_of_work as uow:
            subscription = await uow.subscriptions.get_by_tenant(command.tenant_id)

            if subscription is None:
                subscription = TenantSubscription(
                    tenant_id=command.tenant_id,
                    plan_code=command.plan_code,
                    status=command.status,
                )
                uow.subscriptions.add(subscription)

            subscription.plan_code = command.plan_code
            subscription.status = command.status
            subscription.current_period_end = command.current_period_end
            subscription.cancel_at_period_end = command.cancel_at_period_end
            subscription.provider = _normalized_optional(command.provider)
            subscription.provider_customer_id = _normalized_optional(command.provider_customer_id)
            subscription.provider_subscription_id = _normalized_optional(
                command.provider_subscription_id
            )

            await uow.commit()
            return subscription


def _normalized_optional(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None
