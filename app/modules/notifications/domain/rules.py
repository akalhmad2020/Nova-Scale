from datetime import datetime
from urllib.parse import urlparse

from app.modules.notifications.domain.enums import (
    NotificationAttemptStatus,
    NotificationChannel,
    NotificationStatus,
)


def validate_notification_recipient(
    *,
    channel: NotificationChannel,
    recipient: str,
) -> None:
    normalized_recipient = recipient.strip()

    if not normalized_recipient:
        raise ValueError("Notification recipient cannot be empty.")

    if channel == NotificationChannel.EMAIL:
        _validate_email_recipient(normalized_recipient)
        return

    if channel == NotificationChannel.WEBHOOK:
        _validate_webhook_recipient(normalized_recipient)
        return

    raise ValueError("Unsupported notification channel.")


def can_attempt_delivery(status: NotificationStatus) -> bool:
    return status == NotificationStatus.PENDING


def get_notification_status_after_attempt(
    *,
    attempt_status: NotificationAttemptStatus,
    attempt_number: int,
    max_attempts: int,
) -> NotificationStatus:
    if attempt_number < 1:
        raise ValueError("Attempt number must be at least 1.")

    if max_attempts < 1:
        raise ValueError("Maximum attempts must be at least 1.")

    if attempt_number > max_attempts:
        raise ValueError("Attempt number cannot exceed maximum attempts.")

    if attempt_status == NotificationAttemptStatus.SUCCESS:
        return NotificationStatus.SENT

    if attempt_number >= max_attempts:
        return NotificationStatus.FAILED

    return NotificationStatus.PENDING


def get_notification_retry_delay_seconds(
    *,
    attempt_number: int,
    base_seconds: float,
    max_seconds: float,
) -> float:
    if attempt_number < 1:
        raise ValueError("Attempt number must be at least 1.")

    if base_seconds <= 0:
        raise ValueError("Retry base seconds must be greater than 0.")

    if max_seconds <= 0:
        raise ValueError("Retry maximum seconds must be greater than 0.")

    multiplier = float(2 ** (attempt_number - 1))
    delay: float = base_seconds * multiplier

    return min(delay, max_seconds)


def _validate_email_recipient(recipient: str) -> None:
    local_part, separator, domain = recipient.partition("@")

    if separator != "@" or not local_part or not domain or "." not in domain:
        raise ValueError("Invalid email notification recipient.")


def _validate_webhook_recipient(recipient: str) -> None:
    parsed = urlparse(recipient)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Webhook recipient must use HTTP or HTTPS.")

    if not parsed.netloc:
        raise ValueError("Invalid webhook notification recipient.")


def is_notification_ready_for_delivery(
    *,
    scheduled_at: datetime | None,
    now: datetime,
) -> bool:
    if scheduled_at is None:
        return True

    return scheduled_at <= now
