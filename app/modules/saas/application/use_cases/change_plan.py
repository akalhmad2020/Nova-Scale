from dataclasses import dataclass
from uuid import UUID

from app.modules.saas.application.exceptions import (
    InvalidSubscriptionTransitionError,
    SelfServicePlanUnavailableError,
    SubscriptionNotFoundError,
)
from app.modules.saas.application.ports.subscription_provider import (
    SubscriptionProvider,
)
from app.modules.saas.application.ports.unit_of_work import SubscriptionUnitOfWork
from app.modules.saas.domain.catalog import is_self_service_plan
from app.modules.saas.domain.enums import PlanCode, SubscriptionStatus
from app.modules.saas.infrastructure.models.subscription import TenantSubscription


@dataclass(frozen=True, slots=True)
class ChangePlanCommand:
    tenant_id: UUID
    requested_plan: PlanCode


class ChangePlan:
    def __init__(
        self,
        *,
        unit_of_work: SubscriptionUnitOfWork,
        provider: SubscriptionProvider,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._provider = provider

    async def execute(self, command: ChangePlanCommand) -> TenantSubscription:
        if not is_self_service_plan(command.requested_plan):
            raise SelfServicePlanUnavailableError

        async with self._unit_of_work as uow:
            subscription = await uow.subscriptions.get_by_tenant(command.tenant_id)

            if subscription is None:
                raise SubscriptionNotFoundError

            if subscription.status is not SubscriptionStatus.ACTIVE:
                raise InvalidSubscriptionTransitionError(
                    "Only active subscriptions can change plan through self-service."
                )

            if subscription.plan_code is command.requested_plan:
                return subscription

            activation = await self._provider.activate_plan(
                tenant_id=command.tenant_id,
                current_plan=subscription.plan_code,
                requested_plan=command.requested_plan,
            )

            subscription.plan_code = activation.plan_code
            subscription.status = activation.status
            subscription.current_period_end = activation.current_period_end
            subscription.cancel_at_period_end = activation.cancel_at_period_end
            subscription.provider = activation.provider
            subscription.provider_customer_id = activation.provider_customer_id
            subscription.provider_subscription_id = activation.provider_subscription_id

            await uow.commit()
            return subscription
