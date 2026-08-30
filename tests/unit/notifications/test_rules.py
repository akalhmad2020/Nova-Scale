from datetime import UTC, datetime, timedelta

import pytest

from app.modules.notifications.domain.enums import (
    NotificationAttemptStatus,
    NotificationChannel,
    NotificationStatus,
)
from app.modules.notifications.domain.rules import (
    can_attempt_delivery,
    get_notification_status_after_attempt,
    is_notification_ready_for_delivery,
    validate_notification_recipient,
)


@pytest.mark.parametrize(
    "recipient",
    [
        "billing@example.com",
        "ops@novascale.io",
    ],
)
def test_accepts_valid_email_recipient(recipient: str) -> None:
    validate_notification_recipient(
        channel=NotificationChannel.EMAIL,
        recipient=recipient,
    )


@pytest.mark.parametrize(
    "recipient",
    [
        "",
        "   ",
        "invalid-email",
        "@example.com",
        "billing@localhost",
    ],
)
def test_rejects_invalid_email_recipient(recipient: str) -> None:
    with pytest.raises(ValueError):
        validate_notification_recipient(
            channel=NotificationChannel.EMAIL,
            recipient=recipient,
        )


@pytest.mark.parametrize(
    "recipient",
    [
        "https://erp.example.com/webhooks/novascale",
        "http://localhost:9000/webhook",
    ],
)
def test_accepts_valid_webhook_recipient(recipient: str) -> None:
    validate_notification_recipient(
        channel=NotificationChannel.WEBHOOK,
        recipient=recipient,
    )


@pytest.mark.parametrize(
    "recipient",
    [
        "",
        "   ",
        "erp.example.com/webhook",
        "ftp://example.com/webhook",
        "https:///webhook",
    ],
)
def test_rejects_invalid_webhook_recipient(recipient: str) -> None:
    with pytest.raises(ValueError):
        validate_notification_recipient(
            channel=NotificationChannel.WEBHOOK,
            recipient=recipient,
        )


def test_recipient_is_trimmed_before_validation() -> None:
    validate_notification_recipient(
        channel=NotificationChannel.EMAIL,
        recipient="  billing@example.com  ",
    )

    validate_notification_recipient(
        channel=NotificationChannel.WEBHOOK,
        recipient="  https://erp.example.com/webhooks/novascale  ",
    )


def test_pending_notification_can_be_attempted() -> None:
    assert can_attempt_delivery(NotificationStatus.PENDING) is True


@pytest.mark.parametrize(
    "status",
    [
        NotificationStatus.SENT,
        NotificationStatus.FAILED,
    ],
)
def test_processed_notification_cannot_be_attempted(
    status: NotificationStatus,
) -> None:
    assert can_attempt_delivery(status) is False


def test_successful_attempt_marks_notification_sent() -> None:
    status = get_notification_status_after_attempt(
        attempt_status=NotificationAttemptStatus.SUCCESS,
        attempt_number=1,
        max_attempts=3,
    )

    assert status == NotificationStatus.SENT


def test_retryable_failed_attempt_keeps_notification_pending() -> None:
    status = get_notification_status_after_attempt(
        attempt_status=NotificationAttemptStatus.FAILED,
        attempt_number=2,
        max_attempts=3,
    )

    assert status == NotificationStatus.PENDING


def test_final_failed_attempt_marks_notification_failed() -> None:
    status = get_notification_status_after_attempt(
        attempt_status=NotificationAttemptStatus.FAILED,
        attempt_number=3,
        max_attempts=3,
    )

    assert status == NotificationStatus.FAILED


@pytest.mark.parametrize(
    ("attempt_number", "max_attempts"),
    [
        (0, 3),
        (1, 0),
        (4, 3),
    ],
)
def test_attempt_state_rule_rejects_invalid_attempt_numbers(
    attempt_number: int,
    max_attempts: int,
) -> None:
    with pytest.raises(ValueError):
        get_notification_status_after_attempt(
            attempt_status=NotificationAttemptStatus.FAILED,
            attempt_number=attempt_number,
            max_attempts=max_attempts,
        )


def test_notification_without_schedule_is_ready() -> None:
    now = datetime.now(UTC)

    assert (
        is_notification_ready_for_delivery(
            scheduled_at=None,
            now=now,
        )
        is True
    )


def test_notification_scheduled_in_past_is_ready() -> None:
    now = datetime.now(UTC)

    assert (
        is_notification_ready_for_delivery(
            scheduled_at=now - timedelta(minutes=1),
            now=now,
        )
        is True
    )


def test_notification_scheduled_exactly_now_is_ready() -> None:
    now = datetime.now(UTC)

    assert (
        is_notification_ready_for_delivery(
            scheduled_at=now,
            now=now,
        )
        is True
    )


def test_notification_scheduled_in_future_is_not_ready() -> None:
    now = datetime.now(UTC)

    assert (
        is_notification_ready_for_delivery(
            scheduled_at=now + timedelta(minutes=1),
            now=now,
        )
        is False
    )
