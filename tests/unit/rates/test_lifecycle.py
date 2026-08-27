import pytest

from app.modules.rates.domain.enums import RateQuoteStatus
from app.modules.rates.domain.lifecycle import (
    can_transition_rate_quote_status,
)


@pytest.mark.parametrize(
    ("current_status", "target_status"),
    [
        (
            RateQuoteStatus.DRAFT,
            RateQuoteStatus.QUOTED,
        ),
        (
            RateQuoteStatus.DRAFT,
            RateQuoteStatus.CANCELLED,
        ),
        (
            RateQuoteStatus.QUOTED,
            RateQuoteStatus.ACCEPTED,
        ),
        (
            RateQuoteStatus.QUOTED,
            RateQuoteStatus.EXPIRED,
        ),
        (
            RateQuoteStatus.QUOTED,
            RateQuoteStatus.CANCELLED,
        ),
    ],
)
def test_allows_valid_rate_quote_status_transitions(
    current_status: RateQuoteStatus,
    target_status: RateQuoteStatus,
) -> None:
    assert can_transition_rate_quote_status(
        current_status,
        target_status,
    )


@pytest.mark.parametrize(
    ("current_status", "target_status"),
    [
        (
            RateQuoteStatus.DRAFT,
            RateQuoteStatus.ACCEPTED,
        ),
        (
            RateQuoteStatus.DRAFT,
            RateQuoteStatus.EXPIRED,
        ),
        (
            RateQuoteStatus.QUOTED,
            RateQuoteStatus.DRAFT,
        ),
        (
            RateQuoteStatus.ACCEPTED,
            RateQuoteStatus.DRAFT,
        ),
        (
            RateQuoteStatus.ACCEPTED,
            RateQuoteStatus.CANCELLED,
        ),
        (
            RateQuoteStatus.EXPIRED,
            RateQuoteStatus.QUOTED,
        ),
        (
            RateQuoteStatus.CANCELLED,
            RateQuoteStatus.QUOTED,
        ),
    ],
)
def test_rejects_invalid_rate_quote_status_transitions(
    current_status: RateQuoteStatus,
    target_status: RateQuoteStatus,
) -> None:
    assert not can_transition_rate_quote_status(
        current_status,
        target_status,
    )
