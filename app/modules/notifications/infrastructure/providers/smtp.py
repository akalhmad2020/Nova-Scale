from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

from app.modules.notifications.application.ports.providers import (
    NotificationDeliveryRequest,
    NotificationDeliveryResult,
)
from app.modules.notifications.domain.enums import NotificationChannel


class SMTPEmailNotificationProvider:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        from_address: str,
        username: str | None = None,
        password: str | None = None,
        starttls: bool = True,
        timeout_seconds: float = 15.0,
    ) -> None:
        normalized_host = host.strip()
        normalized_from = from_address.strip()

        if not normalized_host:
            raise ValueError("SMTP host cannot be empty.")

        if not normalized_from:
            raise ValueError("SMTP from address cannot be empty.")

        self._host = normalized_host
        self._port = port
        self._from_address = normalized_from
        self._username = username.strip() if username else None
        self._password = password
        self._starttls = starttls
        self._timeout_seconds = timeout_seconds

    async def send(
        self,
        request: NotificationDeliveryRequest,
    ) -> NotificationDeliveryResult:
        if request.channel != NotificationChannel.EMAIL:
            raise ValueError("SMTP provider only supports email notifications.")

        provider_message_id = await asyncio.to_thread(
            self._send_sync,
            request,
        )

        return NotificationDeliveryResult(
            provider="smtp",
            provider_message_id=provider_message_id,
        )

    def _send_sync(self, request: NotificationDeliveryRequest) -> str | None:
        message = EmailMessage()
        message["From"] = self._from_address
        message["To"] = request.recipient
        message["Subject"] = request.subject or "NovaScale notification"
        message["X-NovaScale-Idempotency-Key"] = request.idempotency_key
        message.set_content(request.body)

        with smtplib.SMTP(
            self._host,
            self._port,
            timeout=self._timeout_seconds,
        ) as smtp:
            smtp.ehlo()

            if self._starttls:
                smtp.starttls()
                smtp.ehlo()

            if self._username:
                if self._password is None:
                    raise RuntimeError("SMTP password is required when SMTP username is set.")
                smtp.login(self._username, self._password)

            refused = smtp.send_message(message)

        if refused:
            refused_recipients = ", ".join(sorted(str(item) for item in refused))
            raise RuntimeError(f"SMTP refused recipients: {refused_recipients}")

        return message.get("Message-ID")
