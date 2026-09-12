from uuid import uuid4

import pytest

from app.modules.saas.domain.enums import PlanCode, SubscriptionStatus
from app.modules.saas.infrastructure.providers.portfolio import (
    PortfolioSubscriptionProvider,
)


@pytest.mark.asyncio
async def test_portfolio_provider_activates_requested_plan_immediately() -> None:
    provider = PortfolioSubscriptionProvider()

    activation = await provider.activate_plan(
        tenant_id=uuid4(),
        current_plan=PlanCode.STARTER,
        requested_plan=PlanCode.PROFESSIONAL,
    )

    assert activation.plan_code is PlanCode.PROFESSIONAL
    assert activation.status is SubscriptionStatus.ACTIVE
    assert activation.provider == "portfolio"
    assert activation.provider_customer_id is None
    assert activation.provider_subscription_id is None
