from datetime import timedelta

import pytest

from app.shared.outbox.application.retry_policy import OutboxRetryPolicy


def test_retry_policy_retries_before_max_attempts() -> None:
    policy = OutboxRetryPolicy(
        max_attempts=5,
    )

    assert policy.should_retry(attempt_count=1) is True
    assert policy.should_retry(attempt_count=4) is True
    assert policy.should_retry(attempt_count=5) is False


def test_retry_policy_uses_exponential_backoff() -> None:
    policy = OutboxRetryPolicy(
        max_attempts=10,
        base_delay=timedelta(seconds=30),
        max_delay=timedelta(minutes=15),
    )

    assert policy.get_delay(attempt_count=1) == timedelta(seconds=30)
    assert policy.get_delay(attempt_count=2) == timedelta(seconds=60)
    assert policy.get_delay(attempt_count=3) == timedelta(seconds=120)
    assert policy.get_delay(attempt_count=4) == timedelta(seconds=240)


def test_retry_policy_caps_backoff_at_max_delay() -> None:
    policy = OutboxRetryPolicy(
        max_attempts=20,
        base_delay=timedelta(minutes=1),
        max_delay=timedelta(minutes=5),
    )

    assert policy.get_delay(attempt_count=10) == timedelta(minutes=5)


def test_retry_policy_rejects_invalid_max_attempts() -> None:
    with pytest.raises(
        ValueError,
        match="Maximum attempts must be at least 1",
    ):
        OutboxRetryPolicy(
            max_attempts=0,
        )


def test_retry_policy_rejects_non_positive_base_delay() -> None:
    with pytest.raises(
        ValueError,
        match="Base retry delay must be positive",
    ):
        OutboxRetryPolicy(
            base_delay=timedelta(0),
        )


def test_retry_policy_rejects_non_positive_max_delay() -> None:
    with pytest.raises(
        ValueError,
        match="Maximum retry delay must be positive",
    ):
        OutboxRetryPolicy(
            max_delay=timedelta(0),
        )


def test_retry_policy_rejects_max_delay_less_than_base_delay() -> None:
    with pytest.raises(
        ValueError,
        match="Maximum retry delay cannot be less than base delay",
    ):
        OutboxRetryPolicy(
            base_delay=timedelta(minutes=10),
            max_delay=timedelta(minutes=5),
        )


@pytest.mark.parametrize(
    "attempt_count",
    [
        0,
        -1,
    ],
)
def test_retry_policy_rejects_invalid_attempt_count(
    attempt_count: int,
) -> None:
    policy = OutboxRetryPolicy()

    with pytest.raises(
        ValueError,
        match="Attempt count must be at least 1",
    ):
        policy.should_retry(
            attempt_count=attempt_count,
        )

    with pytest.raises(
        ValueError,
        match="Attempt count must be at least 1",
    ):
        policy.get_delay(
            attempt_count=attempt_count,
        )
