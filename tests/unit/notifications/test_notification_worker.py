import asyncio

import pytest

from app.modules.notifications.application.services.delivery_processor import (
    NotificationDeliveryBatchResult,
)
from app.workers.notifications import NotificationWorker


class FakeNotificationBatchProcessor:
    def __init__(
        self,
        *,
        results: list[NotificationDeliveryBatchResult] | None = None,
        failures_before_success: int = 0,
    ) -> None:
        self.results = list(results or [])
        self.failures_before_success = failures_before_success
        self.calls = 0

    async def process_batch(
        self,
    ) -> NotificationDeliveryBatchResult:
        self.calls += 1

        if self.calls <= self.failures_before_success:
            raise RuntimeError("temporary processor failure")

        if self.results:
            return self.results.pop(0)

        return NotificationDeliveryBatchResult(
            discovered=0,
            delivered=0,
            retryable_failures=0,
            skipped=0,
            unexpected_failures=0,
        )


async def test_worker_can_be_stopped_gracefully() -> None:
    processor = FakeNotificationBatchProcessor()

    worker = NotificationWorker(
        processor=processor,
        poll_interval_seconds=60.0,
    )

    task = asyncio.create_task(
        worker.run(),
    )

    await asyncio.sleep(0)

    worker.request_stop()

    await asyncio.wait_for(
        task,
        timeout=1.0,
    )

    assert task.done()


async def test_worker_continues_after_unexpected_batch_failure() -> None:
    processor = FakeNotificationBatchProcessor(
        failures_before_success=1,
    )

    worker = NotificationWorker(
        processor=processor,
        poll_interval_seconds=0.001,
    )

    task = asyncio.create_task(
        worker.run(),
    )

    for _ in range(100):
        if processor.calls >= 2:
            break

        await asyncio.sleep(0.001)

    worker.request_stop()

    await asyncio.wait_for(
        task,
        timeout=1.0,
    )

    assert processor.calls >= 2


@pytest.mark.parametrize(
    "poll_interval_seconds",
    [
        0.0,
        -1.0,
    ],
)
def test_worker_rejects_invalid_poll_interval(
    poll_interval_seconds: float,
) -> None:
    processor = FakeNotificationBatchProcessor()

    with pytest.raises(
        ValueError,
        match="Poll interval seconds must be greater than 0",
    ):
        NotificationWorker(
            processor=processor,
            poll_interval_seconds=poll_interval_seconds,
        )
