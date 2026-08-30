from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import suppress
from typing import Protocol

from app.core.config import get_settings
from app.core.database import SessionFactory, dispose_engine
from app.core.logging import configure_logging
from app.modules.notifications.application.services.delivery_processor import (
    NotificationDeliveryBatchResult,
    NotificationDeliveryProcessor,
)
from app.modules.notifications.infrastructure.providers.runtime import (
    build_notification_provider_registry,
)

logger = logging.getLogger(__name__)


class NotificationBatchProcessor(Protocol):
    async def process_batch(
        self,
    ) -> NotificationDeliveryBatchResult: ...


class NotificationWorker:
    def __init__(
        self,
        *,
        processor: NotificationBatchProcessor,
        poll_interval_seconds: float,
    ) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("Poll interval seconds must be greater than 0.")

        self._processor = processor
        self._poll_interval_seconds = poll_interval_seconds
        self._stop_event = asyncio.Event()

    def request_stop(self) -> None:
        if self._stop_event.is_set():
            return

        logger.info("Notification worker shutdown requested.")
        self._stop_event.set()

    async def run(self) -> None:
        logger.info(
            "Notification worker started. poll_interval_seconds=%s",
            self._poll_interval_seconds,
        )

        while not self._stop_event.is_set():
            try:
                result = await self._processor.process_batch()

                if result.discovered > 0:
                    logger.info(
                        "Notification batch processed. "
                        "discovered=%s delivered=%s "
                        "retryable_failures=%s skipped=%s "
                        "unexpected_failures=%s",
                        result.discovered,
                        result.delivered,
                        result.retryable_failures,
                        result.skipped,
                        result.unexpected_failures,
                    )

            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Unexpected error while processing notification batch.")

            if self._stop_event.is_set():
                break

            with suppress(TimeoutError):
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._poll_interval_seconds,
                )

        logger.info("Notification worker stopped.")


def install_signal_handlers(
    worker: NotificationWorker,
) -> None:
    loop = asyncio.get_running_loop()

    for shutdown_signal in (
        signal.SIGINT,
        signal.SIGTERM,
    ):
        loop.add_signal_handler(
            shutdown_signal,
            worker.request_stop,
        )


async def run_worker() -> None:
    settings = get_settings()

    configure_logging(settings.log_level)

    provider_registry = build_notification_provider_registry(
        app_env=settings.app_env,
    )

    processor = NotificationDeliveryProcessor(
        session_factory=SessionFactory,
        provider_resolver=provider_registry,
        batch_size=settings.notification_worker_batch_size,
        max_attempts=settings.notification_worker_max_attempts,
        retry_base_seconds=(settings.notification_worker_retry_base_seconds),
        retry_max_seconds=(settings.notification_worker_retry_max_seconds),
    )

    worker = NotificationWorker(
        processor=processor,
        poll_interval_seconds=(settings.notification_worker_poll_interval_seconds),
    )

    install_signal_handlers(worker)

    try:
        await worker.run()
    finally:
        await dispose_engine()


def main() -> None:
    asyncio.run(
        run_worker(),
    )


if __name__ == "__main__":
    main()
