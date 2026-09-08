from __future__ import annotations

from urllib.parse import urlparse

import httpx

from app.modules.notifications.application.ports.providers import (
    NotificationDeliveryRequest,
    NotificationDeliveryResult,
)
from app.modules.notifications.domain.enums import NotificationChannel


class HTTPWebhookNotificationProvider:
    def __init__(
        self,
        *,
        allowed_hosts: tuple[str, ...],
        timeout_seconds: float = 15.0,
        require_https: bool = True,
    ) -> None:
        self._allowed_hosts = frozenset(
            host.lower().strip() for host in allowed_hosts if host.strip()
        )
        self._timeout_seconds = timeout_seconds
        self._require_https = require_https

    async def send(
        self,
        request: NotificationDeliveryRequest,
    ) -> NotificationDeliveryResult:
        if request.channel != NotificationChannel.WEBHOOK:
            raise ValueError("HTTP webhook provider only supports webhook notifications.")

        self._validate_recipient(request.recipient)

        payload = {
            "event_type": "notification",
            "subject": request.subject,
            "body": request.body,
            "idempotency_key": request.idempotency_key,
        }

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(
                request.recipient,
                json=payload,
                headers={
                    "Idempotency-Key": request.idempotency_key,
                    "User-Agent": "NovaScale-Notifications/2.0",
                },
            )
            response.raise_for_status()

        provider_message_id = response.headers.get("X-Request-ID")

        return NotificationDeliveryResult(
            provider="http-webhook",
            provider_message_id=provider_message_id,
        )

    def _validate_recipient(self, recipient: str) -> None:
        parsed = urlparse(recipient)
        hostname = (parsed.hostname or "").lower()

        if self._require_https and parsed.scheme != "https":
            raise ValueError("Production webhooks must use HTTPS.")

        if not hostname:
            raise ValueError("Webhook recipient must contain a hostname.")

        if not self._allowed_hosts:
            raise ValueError("No outbound webhook hosts are allowlisted.")

        if hostname not in self._allowed_hosts:
            raise ValueError(f"Webhook host '{hostname}' is not allowlisted.")
