from __future__ import annotations

import logging
from uuid import uuid4

from app.modules.notifications.application.ports.providers import (
    NotificationDeliveryRequest,
    NotificationDeliveryResult,
)
from app.modules.notifications.domain.enums import NotificationChannel

logger = logging.getLogger(__name__)


class LoggingEmailNotificationProvider:
    async def send(
        self,
        request: NotificationDeliveryRequest,
    ) -> NotificationDeliveryResult:
        if request.channel != NotificationChannel.EMAIL:
            raise ValueError("Logging email provider only supports email notifications.")

        provider_message_id = f"local-email-{uuid4()}"

        logger.info(
            "Email notification delivered by local logging provider. "
            "recipient=%s idempotency_key=%s provider_message_id=%s",
            request.recipient,
            request.idempotency_key,
            provider_message_id,
        )

        return NotificationDeliveryResult(
            provider="logging-email",
            provider_message_id=provider_message_id,
        )


class LoggingWebhookNotificationProvider:
    async def send(
        self,
        request: NotificationDeliveryRequest,
    ) -> NotificationDeliveryResult:
        if request.channel != NotificationChannel.WEBHOOK:
            raise ValueError("Logging webhook provider only supports webhook notifications.")

        provider_message_id = f"local-webhook-{uuid4()}"

        logger.info(
            "Webhook notification delivered by local logging provider. "
            "recipient=%s idempotency_key=%s provider_message_id=%s",
            request.recipient,
            request.idempotency_key,
            provider_message_id,
        )

        return NotificationDeliveryResult(
            provider="logging-webhook",
            provider_message_id=provider_message_id,
        )
