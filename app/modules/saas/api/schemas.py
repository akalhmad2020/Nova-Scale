from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.saas.domain.enums import PlanCode, SubscriptionStatus


class PlanEntitlementsResponse(BaseModel):
    ai_assistant: bool
    rag_indexing: bool
    outbound_webhooks: bool
    team_member_limit: int | None


class PlanResponse(BaseModel):
    code: PlanCode
    name: str
    description: str
    display_order: int
    recommended: bool
    self_service: bool
    entitlements: PlanEntitlementsResponse


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    plan_code: PlanCode
    status: SubscriptionStatus
    current_period_end: datetime | None
    cancel_at_period_end: bool
    provider: str | None
    created_at: datetime
    updated_at: datetime


class ChangePlanRequest(BaseModel):
    plan_code: PlanCode
