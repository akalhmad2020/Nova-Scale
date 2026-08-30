from dataclasses import dataclass
from typing import Protocol

from app.modules.notifications.domain.enums import NotificationChannel


@dataclass(frozen=True)
class NotificationDeliveryRequest:
    channel: NotificationChannel
    recipient: str
    subject: str | None
    body: str
    idempotency_key: str


@dataclass(frozen=True)
class NotificationDeliveryResult:
    provider: str
    provider_message_id: str | None


class NotificationProvider(Protocol):
    async def send(
        self,
        request: NotificationDeliveryRequest,
    ) -> NotificationDeliveryResult: ...


class NotificationProviderResolver(Protocol):
    def resolve(
        self,
        channel: NotificationChannel,
    ) -> NotificationProvider: ...
