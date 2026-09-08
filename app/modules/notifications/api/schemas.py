from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.notifications.domain.enums import (
    NotificationAttemptStatus,
    NotificationChannel,
    NotificationStatus,
)


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    event_type: str
    recipient: str
    channel: NotificationChannel
    subject: str | None
    body: str
    status: NotificationStatus
    scheduled_at: datetime | None
    sent_at: datetime | None
    failed_at: datetime | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime


class NotificationAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notification_id: UUID
    attempt_number: int
    status: NotificationAttemptStatus
    provider: str
    provider_message_id: str | None
    error: str | None
    attempted_at: datetime


class NotificationDetailsResponse(NotificationResponse):
    attempts: list[NotificationAttemptResponse]
