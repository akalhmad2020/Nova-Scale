from dataclasses import dataclass
from uuid import UUID

from app.modules.entitlements.domain.catalog import (
    Entitlements,
    PlanEntitlementSet,
    get_plan_entitlements,
)
from app.modules.saas.application.exceptions import SubscriptionNotFoundError
from app.modules.saas.application.ports.unit_of_work import SubscriptionUnitOfWork
from app.modules.saas.domain.enums import PlanCode, SubscriptionStatus


@dataclass(frozen=True, slots=True)
class EntitlementSnapshot:
    tenant_id: UUID
    plan_code: PlanCode
    subscription_status: SubscriptionStatus
    ai_assistant: bool
    rag_indexing: bool
    outbound_webhooks: bool
    team_member_limit: int | None

    def is_enabled(self, entitlement_code: str) -> bool:
        values = {
            Entitlements.AI_ASSISTANT: self.ai_assistant,
            Entitlements.RAG_INDEXING: self.rag_indexing,
            Entitlements.OUTBOUND_WEBHOOKS: self.outbound_webhooks,
        }

        try:
            return values[entitlement_code]
        except KeyError as exc:
            raise ValueError(f"Unknown boolean entitlement: {entitlement_code}") from exc


class GetEntitlements:
    def __init__(self, unit_of_work: SubscriptionUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, tenant_id: UUID) -> EntitlementSnapshot:
        async with self._unit_of_work as uow:
            subscription = await uow.subscriptions.get_by_tenant(tenant_id)

            if subscription is None:
                raise SubscriptionNotFoundError

            entitlements = _effective_entitlements(
                plan_code=subscription.plan_code,
                status=subscription.status,
            )

            return EntitlementSnapshot(
                tenant_id=tenant_id,
                plan_code=subscription.plan_code,
                subscription_status=subscription.status,
                ai_assistant=entitlements.ai_assistant,
                rag_indexing=entitlements.rag_indexing,
                outbound_webhooks=entitlements.outbound_webhooks,
                team_member_limit=entitlements.team_member_limit,
            )


def _effective_entitlements(
    *,
    plan_code: PlanCode,
    status: SubscriptionStatus,
) -> PlanEntitlementSet:
    catalog = get_plan_entitlements(plan_code)

    if status == SubscriptionStatus.ACTIVE:
        return catalog

    return PlanEntitlementSet(
        ai_assistant=False,
        rag_indexing=False,
        outbound_webhooks=False,
        team_member_limit=catalog.team_member_limit,
    )
