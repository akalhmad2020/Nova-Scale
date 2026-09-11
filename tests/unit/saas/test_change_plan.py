from types import TracebackType
from uuid import UUID, uuid4

import pytest

from app.modules.saas.application.exceptions import (
    InvalidSubscriptionTransitionError,
    SelfServicePlanUnavailableError,
)
from app.modules.saas.application.use_cases.change_plan import (
    ChangePlan,
    ChangePlanCommand,
)
from app.modules.saas.domain.enums import PlanCode, SubscriptionStatus
from app.modules.saas.infrastructure.models.subscription import TenantSubscription
from app.modules.saas.infrastructure.providers.portfolio import (
    PortfolioSubscriptionProvider,
)


class FakeSubscriptionRepository:
    def __init__(self, subscription: TenantSubscription) -> None:
        self.subscription = subscription

    async def get_by_tenant(self, tenant_id: UUID) -> TenantSubscription | None:
        if self.subscription.tenant_id == tenant_id:
            return self.subscription
        return None

    def add(self, subscription: TenantSubscription) -> None:
        self.subscription = subscription


class FakeSubscriptionUnitOfWork:
    def __init__(self, subscription: TenantSubscription) -> None:
        self.subscriptions = FakeSubscriptionRepository(subscription)
        self.commits = 0

    async def __aenter__(self) -> "FakeSubscriptionUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None


def make_subscription(
    *,
    plan: PlanCode = PlanCode.STARTER,
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
) -> TenantSubscription:
    return TenantSubscription(
        tenant_id=uuid4(),
        plan_code=plan,
        status=status,
        cancel_at_period_end=False,
    )


@pytest.mark.asyncio
async def test_change_plan_activates_professional_in_portfolio_mode() -> None:
    subscription = make_subscription()
    uow = FakeSubscriptionUnitOfWork(subscription)
    use_case = ChangePlan(
        unit_of_work=uow,
        provider=PortfolioSubscriptionProvider(),
    )

    result = await use_case.execute(
        ChangePlanCommand(
            tenant_id=subscription.tenant_id,
            requested_plan=PlanCode.PROFESSIONAL,
        )
    )

    assert result.plan_code is PlanCode.PROFESSIONAL
    assert result.status is SubscriptionStatus.ACTIVE
    assert result.provider == "portfolio"
    assert uow.commits == 1


@pytest.mark.asyncio
async def test_change_plan_rejects_enterprise_self_service() -> None:
    subscription = make_subscription()
    use_case = ChangePlan(
        unit_of_work=FakeSubscriptionUnitOfWork(subscription),
        provider=PortfolioSubscriptionProvider(),
    )

    with pytest.raises(SelfServicePlanUnavailableError):
        await use_case.execute(
            ChangePlanCommand(
                tenant_id=subscription.tenant_id,
                requested_plan=PlanCode.ENTERPRISE,
            )
        )


@pytest.mark.asyncio
async def test_change_plan_rejects_non_active_subscription() -> None:
    subscription = make_subscription(status=SubscriptionStatus.SUSPENDED)
    use_case = ChangePlan(
        unit_of_work=FakeSubscriptionUnitOfWork(subscription),
        provider=PortfolioSubscriptionProvider(),
    )

    with pytest.raises(InvalidSubscriptionTransitionError):
        await use_case.execute(
            ChangePlanCommand(
                tenant_id=subscription.tenant_id,
                requested_plan=PlanCode.PROFESSIONAL,
            )
        )
