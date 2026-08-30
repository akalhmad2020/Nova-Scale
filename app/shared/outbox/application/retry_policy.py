from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class OutboxRetryPolicy:
    max_attempts: int = 5
    base_delay: timedelta = timedelta(seconds=30)
    max_delay: timedelta = timedelta(minutes=15)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("Maximum attempts must be at least 1.")

        if self.base_delay <= timedelta(0):
            raise ValueError("Base retry delay must be positive.")

        if self.max_delay <= timedelta(0):
            raise ValueError("Maximum retry delay must be positive.")

        if self.max_delay < self.base_delay:
            raise ValueError("Maximum retry delay cannot be less than base delay.")

    def should_retry(
        self,
        *,
        attempt_count: int,
    ) -> bool:
        if attempt_count < 1:
            raise ValueError("Attempt count must be at least 1.")

        return attempt_count < self.max_attempts

    def get_delay(
        self,
        *,
        attempt_count: int,
    ) -> timedelta:
        if attempt_count < 1:
            raise ValueError("Attempt count must be at least 1.")

        multiplier = 2 ** (attempt_count - 1)
        delay_seconds = self.base_delay.total_seconds() * multiplier
        delay = timedelta(seconds=delay_seconds)

        if delay > self.max_delay:
            return self.max_delay

        return delay
