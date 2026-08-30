from datetime import timedelta

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.core.config import Settings
from app.modules.notifications.infrastructure.outbox.registry import (
    build_notification_outbox_handler_registry,
)
from app.shared.outbox.application.processing_service import (
    OutboxProcessingService,
)
from app.shared.outbox.application.retry_policy import (
    OutboxRetryPolicy,
)
from app.shared.outbox.infrastructure.unit_of_work import (
    SQLAlchemyOutboxUnitOfWork,
)


def build_outbox_processing_service(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> OutboxProcessingService:
    handler_registry = build_notification_outbox_handler_registry(
        session_factory,
    )

    retry_policy = OutboxRetryPolicy(
        max_attempts=settings.outbox_worker_max_attempts,
        base_delay=timedelta(
            seconds=settings.outbox_worker_retry_base_seconds,
        ),
        max_delay=timedelta(
            seconds=settings.outbox_worker_retry_max_seconds,
        ),
    )

    return OutboxProcessingService(
        unit_of_work_factory=lambda: SQLAlchemyOutboxUnitOfWork(
            session_factory,
        ),
        handler_resolver=handler_registry,
        retry_policy=retry_policy,
        lease_duration=timedelta(
            seconds=settings.outbox_worker_lease_seconds,
        ),
        batch_size=settings.outbox_worker_batch_size,
    )
