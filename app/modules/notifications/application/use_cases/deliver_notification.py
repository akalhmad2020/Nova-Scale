from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.modules.notifications.application.exceptions import (
    NotificationAlreadyProcessedError,
    NotificationDeliveryError,
    NotificationNotFoundError,
    NotificationNotReadyError,
)
from app.modules.notifications.application.ports.providers import (
    NotificationDeliveryRequest,
    NotificationProviderResolver,
)
from app.modules.notifications.application.ports.unit_of_work import (
    NotificationUnitOfWork,
)
from app.modules.notifications.domain.enums import (
    NotificationAttemptStatus,
    NotificationChannel,
    NotificationStatus,
)
from app.modules.notifications.domain.rules import (
    can_attempt_delivery,
    get_notification_retry_delay_seconds,
    get_notification_status_after_attempt,
    is_notification_ready_for_delivery,
)
from app.modules.notifications.infrastructure.models.notification import (
    Notification,
)
from app.modules.notifications.infrastructure.models.notification_attempt import (
    NotificationAttempt,
)


class DeliverNotificationUseCase:
    def __init__(
        self,
        *,
        unit_of_work: NotificationUnitOfWork,
        provider_resolver: NotificationProviderResolver,
        max_attempts: int = 3,
        retry_base_seconds: float = 30.0,
        retry_max_seconds: float = 900.0,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("Maximum attempts must be at least 1.")

        if retry_base_seconds <= 0:
            raise ValueError("Retry base seconds must be greater than 0.")

        if retry_max_seconds <= 0:
            raise ValueError("Retry maximum seconds must be greater than 0.")

        self._unit_of_work = unit_of_work
        self._provider_resolver = provider_resolver
        self._max_attempts = max_attempts
        self._retry_base_seconds = retry_base_seconds
        self._retry_max_seconds = retry_max_seconds

    async def execute(
        self,
        *,
        tenant_id: UUID,
        notification_id: UUID,
    ) -> Notification:
        notification = await self._unit_of_work.notifications.get_by_id_for_update(
            tenant_id=tenant_id,
            notification_id=notification_id,
        )

        if notification is None:
            raise NotificationNotFoundError

        status = NotificationStatus(notification.status)

        if not can_attempt_delivery(status):
            raise NotificationAlreadyProcessedError

        now = datetime.now(UTC)

        if not is_notification_ready_for_delivery(
            scheduled_at=notification.scheduled_at,
            now=now,
        ):
            raise NotificationNotReadyError

        latest_attempt = await self._unit_of_work.attempts.get_latest_attempt(
            tenant_id=tenant_id,
            notification_id=notification_id,
        )

        attempt_number = 1 if latest_attempt is None else latest_attempt.attempt_number + 1

        if attempt_number > self._max_attempts:
            raise NotificationAlreadyProcessedError

        channel = NotificationChannel(notification.channel)

        provider = self._provider_resolver.resolve(channel)

        request = NotificationDeliveryRequest(
            channel=channel,
            recipient=notification.recipient,
            subject=notification.subject,
            body=notification.body,
            idempotency_key=notification.idempotency_key,
        )

        attempted_at = now

        try:
            result = await provider.send(request)
        except Exception as exc:
            attempt = NotificationAttempt(
                tenant_id=tenant_id,
                notification_id=notification.id,
                attempt_number=attempt_number,
                status=NotificationAttemptStatus.FAILED.value,
                provider=type(provider).__name__,
                provider_message_id=None,
                error=str(exc),
                attempted_at=attempted_at,
            )

            next_status = get_notification_status_after_attempt(
                attempt_status=NotificationAttemptStatus.FAILED,
                attempt_number=attempt_number,
                max_attempts=self._max_attempts,
            )

            notification.status = next_status.value

            if next_status == NotificationStatus.FAILED:
                notification.failed_at = attempted_at
                notification.failure_reason = str(exc)
                notification.scheduled_at = None
            else:
                retry_delay_seconds = get_notification_retry_delay_seconds(
                    attempt_number=attempt_number,
                    base_seconds=self._retry_base_seconds,
                    max_seconds=self._retry_max_seconds,
                )

                notification.scheduled_at = attempted_at + timedelta(
                    seconds=retry_delay_seconds,
                )

                notification.failed_at = None
                notification.failure_reason = None

            try:
                await self._unit_of_work.attempts.add(attempt)
                await self._unit_of_work.commit()
            except Exception:
                await self._unit_of_work.rollback()
                raise

            raise NotificationDeliveryError(str(exc)) from exc

        attempt = NotificationAttempt(
            tenant_id=tenant_id,
            notification_id=notification.id,
            attempt_number=attempt_number,
            status=NotificationAttemptStatus.SUCCESS.value,
            provider=result.provider,
            provider_message_id=result.provider_message_id,
            error=None,
            attempted_at=attempted_at,
        )

        notification.status = NotificationStatus.SENT.value
        notification.sent_at = attempted_at
        notification.failed_at = None
        notification.failure_reason = None
        notification.scheduled_at = None

        try:
            await self._unit_of_work.attempts.add(attempt)
            await self._unit_of_work.commit()
        except Exception:
            await self._unit_of_work.rollback()
            raise

        return notification
