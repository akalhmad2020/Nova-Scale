from app.core.database import SessionFactory
from app.modules.saas.application.use_cases.get_subscription import GetSubscription
from app.modules.saas.infrastructure.unit_of_work import SQLAlchemySubscriptionUnitOfWork


def get_subscription_use_case() -> GetSubscription:
    return GetSubscription(
        unit_of_work=SQLAlchemySubscriptionUnitOfWork(SessionFactory),
    )
