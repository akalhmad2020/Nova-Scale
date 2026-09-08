from dataclasses import dataclass
from uuid import UUID

from app.modules.saas.application.exceptions import SubscriptionNotFoundError
from app.modules.saas.application.ports.unit_of_work import SubscriptionUnitOfWork
from app.modules.saas.infrastructure.models.subscription import TenantSubscription


@dataclass(frozen=True, slots=True)
class GetSubscriptionQuery:
    tenant_id: UUID


class GetSubscription:
    def __init__(self, unit_of_work: SubscriptionUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, query: GetSubscriptionQuery) -> TenantSubscription:
        async with self._unit_of_work as uow:
            subscription = await uow.subscriptions.get_by_tenant(query.tenant_id)

            if subscription is None:
                raise SubscriptionNotFoundError

            return subscription
