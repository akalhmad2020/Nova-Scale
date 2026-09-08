from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.saas.domain.enums import PlanCode, SubscriptionStatus


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
