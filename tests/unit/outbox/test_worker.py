import asyncio
from datetime import datetime

from app.workers.outbox import OutboxWorker


class FakeProcessor:
    def __init__(
        self,
        *,
        stop_after_calls: int | None = None,
        fail_calls: int = 0,
    ) -> None:
        self.stop_after_calls = stop_after_calls
        self.fail_calls = fail_calls
        self.calls = 0
        self.worker: OutboxWorker | None = None

    async def process_batch(
        self,
        *,
        now: datetime,
    ) -> int:
        self.calls += 1

        if self.calls <= self.fail_calls:
            raise RuntimeError("Simulated processor failure.")

        if (
            self.worker is not None
            and self.stop_after_calls is not None
            and self.calls >= self.stop_after_calls
        ):
            self.worker.request_stop()

        return 1


async def test_worker_processes_batches_until_stopped() -> None:
    processor = FakeProcessor(
        stop_after_calls=2,
    )

    worker = OutboxWorker(
        processor=processor,
        poll_interval_seconds=0.001,
    )

    processor.worker = worker

    await asyncio.wait_for(
        worker.run(),
        timeout=1,
    )

    assert processor.calls == 2


async def test_worker_survives_processor_failure() -> None:
    processor = FakeProcessor(
        stop_after_calls=2,
        fail_calls=1,
    )

    worker = OutboxWorker(
        processor=processor,
        poll_interval_seconds=0.001,
    )

    processor.worker = worker

    await asyncio.wait_for(
        worker.run(),
        timeout=1,
    )

    assert processor.calls == 2


async def test_worker_can_be_stopped_before_run() -> None:
    processor = FakeProcessor()

    worker = OutboxWorker(
        processor=processor,
        poll_interval_seconds=0.001,
    )

    worker.request_stop()

    await asyncio.wait_for(
        worker.run(),
        timeout=1,
    )

    assert processor.calls == 0


async def test_worker_stop_request_is_idempotent() -> None:
    processor = FakeProcessor()

    worker = OutboxWorker(
        processor=processor,
        poll_interval_seconds=0.001,
    )

    worker.request_stop()
    worker.request_stop()

    await asyncio.wait_for(
        worker.run(),
        timeout=1,
    )

    assert processor.calls == 0
