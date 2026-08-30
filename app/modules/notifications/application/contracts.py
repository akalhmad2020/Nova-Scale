from dataclasses import dataclass
from datetime import datetime

from app.modules.notifications.domain.enums import NotificationChannel


@dataclass(frozen=True)
class NotificationIntent:
    event_type: str
    recipient: str
    channel: NotificationChannel
    subject: str | None
    body: str
    idempotency_key: str
    scheduled_at: datetime | None = None
