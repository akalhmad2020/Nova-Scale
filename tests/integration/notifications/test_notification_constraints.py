from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.domain.enums import (
    NotificationAttemptStatus,
    NotificationChannel,
    NotificationStatus,
)
from app.modules.notifications.infrastructure.models.notification import (
    Notification,
)
from app.modules.notifications.infrastructure.models.notification_attempt import (
    NotificationAttempt,
)

pytestmark = pytest.mark.integration


def make_notification(
    *,
    tenant_id: UUID | None = None,
    idempotency_key: str | None = None,
) -> Notification:
    return Notification(
        tenant_id=tenant_id or uuid4(),
        event_type="invoice.issued",
        recipient="billing@example.com",
        channel=NotificationChannel.EMAIL.value,
        subject="Invoice issued",
        body="Your invoice has been issued.",
        status=NotificationStatus.PENDING.value,
        idempotency_key=idempotency_key or str(uuid4()),
    )


async def persist_notification(
    db_session: AsyncSession,
    notification: Notification,
) -> None:
    db_session.add(notification)
    await db_session.flush()


async def test_notification_idempotency_key_is_unique_per_tenant(
    db_session: AsyncSession,
) -> None:
    tenant_id = uuid4()
    idempotency_key = "invoice-issued:invoice-123"

    first = make_notification(
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
    )
    second = make_notification(
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
    )

    db_session.add_all([first, second])

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_same_idempotency_key_is_allowed_for_different_tenants(
    db_session: AsyncSession,
) -> None:
    idempotency_key = "invoice-issued:invoice-123"

    first = make_notification(
        tenant_id=uuid4(),
        idempotency_key=idempotency_key,
    )
    second = make_notification(
        tenant_id=uuid4(),
        idempotency_key=idempotency_key,
    )

    db_session.add_all([first, second])
    await db_session.flush()


async def test_notification_attempt_cannot_reference_notification_from_other_tenant(
    db_session: AsyncSession,
) -> None:
    notification = make_notification()
    await persist_notification(db_session, notification)

    attempt = NotificationAttempt(
        tenant_id=uuid4(),
        notification_id=notification.id,
        attempt_number=1,
        status=NotificationAttemptStatus.SUCCESS.value,
        provider="fake-email",
        provider_message_id="message-123",
        error=None,
        attempted_at=datetime.now(UTC),
    )

    db_session.add(attempt)

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_attempt_number_is_unique_per_notification(
    db_session: AsyncSession,
) -> None:
    notification = make_notification()
    await persist_notification(db_session, notification)

    first = NotificationAttempt(
        tenant_id=notification.tenant_id,
        notification_id=notification.id,
        attempt_number=1,
        status=NotificationAttemptStatus.FAILED.value,
        provider="fake-email",
        provider_message_id=None,
        error="Temporary provider failure.",
        attempted_at=datetime.now(UTC),
    )
    second = NotificationAttempt(
        tenant_id=notification.tenant_id,
        notification_id=notification.id,
        attempt_number=1,
        status=NotificationAttemptStatus.SUCCESS.value,
        provider="fake-email",
        provider_message_id="message-123",
        error=None,
        attempted_at=datetime.now(UTC),
    )

    db_session.add_all([first, second])

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_notification_rejects_invalid_channel(
    db_session: AsyncSession,
) -> None:
    notification = make_notification()
    notification.channel = "sms"

    db_session.add(notification)

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_notification_rejects_invalid_status(
    db_session: AsyncSession,
) -> None:
    notification = make_notification()
    notification.status = "unknown"

    db_session.add(notification)

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_notification_attempt_rejects_non_positive_attempt_number(
    db_session: AsyncSession,
) -> None:
    notification = make_notification()
    await persist_notification(db_session, notification)

    attempt = NotificationAttempt(
        tenant_id=notification.tenant_id,
        notification_id=notification.id,
        attempt_number=0,
        status=NotificationAttemptStatus.FAILED.value,
        provider="fake-email",
        provider_message_id=None,
        error="Temporary provider failure.",
        attempted_at=datetime.now(UTC),
    )

    db_session.add(attempt)

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_notification_attempt_rejects_invalid_status(
    db_session: AsyncSession,
) -> None:
    notification = make_notification()
    await persist_notification(db_session, notification)

    attempt = NotificationAttempt(
        tenant_id=notification.tenant_id,
        notification_id=notification.id,
        attempt_number=1,
        status="pending",
        provider="fake-email",
        provider_message_id=None,
        error=None,
        attempted_at=datetime.now(UTC),
    )

    db_session.add(attempt)

    with pytest.raises(IntegrityError):
        await db_session.flush()
