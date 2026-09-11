from app.core.config import get_settings
from app.core.database import SessionFactory
from app.modules.saas.application.ports.subscription_provider import (
    SubscriptionProvider,
)
from app.modules.saas.application.use_cases.change_plan import ChangePlan
from app.modules.saas.application.use_cases.get_subscription import GetSubscription
from app.modules.saas.infrastructure.providers import (
    PortfolioSubscriptionProvider,
    StripeSubscriptionProviderPlaceholder,
)
from app.modules.saas.infrastructure.unit_of_work import SQLAlchemySubscriptionUnitOfWork


def get_subscription_use_case() -> GetSubscription:
    return GetSubscription(
        unit_of_work=SQLAlchemySubscriptionUnitOfWork(SessionFactory),
    )


def get_subscription_provider() -> SubscriptionProvider:
    settings = get_settings()

    if settings.billing_provider == "portfolio":
        return PortfolioSubscriptionProvider()

    return StripeSubscriptionProviderPlaceholder()


def get_change_plan_use_case() -> ChangePlan:
    return ChangePlan(
        unit_of_work=SQLAlchemySubscriptionUnitOfWork(SessionFactory),
        provider=get_subscription_provider(),
    )
