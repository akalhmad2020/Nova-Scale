import asyncio
import logging
import signal
from contextlib import suppress
from datetime import UTC, datetime
from typing import Protocol

from app.core.config import get_settings
from app.core.database import SessionFactory, dispose_engine
from app.core.logging import configure_logging
from app.shared.outbox.infrastructure.runtime import (
    build_outbox_processing_service,
)

logger = logging.getLogger(__name__)


class OutboxBatchProcessor(Protocol):
    async def process_batch(
        self,
        *,
        now: datetime,
    ) -> int: ...


class OutboxWorker:
    def __init__(
        self,
        *,
        processor: OutboxBatchProcessor,
        poll_interval_seconds: float,
    ) -> None:
        self._processor = processor
        self._poll_interval_seconds = poll_interval_seconds
        self._stop_event = asyncio.Event()

    def request_stop(self) -> None:
        if self._stop_event.is_set():
            return

        logger.info("Outbox worker shutdown requested.")
        self._stop_event.set()

    async def run(self) -> None:
        logger.info(
            "Outbox worker started. poll_interval_seconds=%s",
            self._poll_interval_seconds,
        )

        while not self._stop_event.is_set():
            try:
                processed_count = await self._processor.process_batch(
                    now=datetime.now(UTC),
                )

                if processed_count > 0:
                    logger.info(
                        "Outbox batch processed. message_count=%s",
                        processed_count,
                    )

            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Unexpected error while processing outbox batch.")

            if self._stop_event.is_set():
                break

            with suppress(TimeoutError):
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._poll_interval_seconds,
                )

        logger.info("Outbox worker stopped.")


def install_signal_handlers(
    worker: OutboxWorker,
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

    configure_logging(
        settings.log_level,
    )

    processor = build_outbox_processing_service(
        session_factory=SessionFactory,
        settings=settings,
    )

    worker = OutboxWorker(
        processor=processor,
        poll_interval_seconds=settings.outbox_worker_poll_interval_seconds,
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
