from uuid import UUID

from pydantic import BaseModel

from app.modules.saas.domain.enums import PlanCode, SubscriptionStatus


class EntitlementsResponse(BaseModel):
    tenant_id: UUID
    plan_code: PlanCode
    subscription_status: SubscriptionStatus
    ai_assistant: bool
    rag_indexing: bool
    outbound_webhooks: bool
    team_member_limit: int | None
