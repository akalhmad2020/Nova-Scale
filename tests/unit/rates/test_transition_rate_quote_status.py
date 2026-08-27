from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.rates.application.exceptions import (
    InvalidRateQuoteStatusTransitionError,
    RateQuoteNotFoundError,
)
from app.modules.rates.application.use_cases.transition_rate_quote_status import (
    TransitionRateQuoteStatus,
    TransitionRateQuoteStatusCommand,
)
from app.modules.rates.domain.enums import RateQuoteStatus
from app.modules.rates.infrastructure.models.rate_quote import RateQuote
from tests.unit.rates.fakes import FakeUnitOfWork


def make_rate_quote(
    *,
    tenant_id: UUID,
    status: RateQuoteStatus,
) -> RateQuote:
    rate_quote = RateQuote(
        tenant_id=tenant_id,
        shipment_id=uuid4(),
        currency="USD",
        base_amount=Decimal("100.00"),
        surcharge_amount=Decimal("10.00"),
        total_amount=Decimal("110.00"),
        status=status,
        expires_at=None,
    )
    rate_quote.id = uuid4()

    return rate_quote


async def test_transition_rate_quote_status_updates_status() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    rate_quote = make_rate_quote(
        tenant_id=tenant_id,
        status=RateQuoteStatus.DRAFT,
    )

    uow.rate_quotes.add(rate_quote)

    result = await TransitionRateQuoteStatus(uow).execute(
        TransitionRateQuoteStatusCommand(
            tenant_id=tenant_id,
            rate_quote_id=rate_quote.id,
            status=RateQuoteStatus.QUOTED,
        )
    )

    assert result.status == RateQuoteStatus.QUOTED

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.refreshed is True
    assert uow.rolled_back is False


async def test_transition_rate_quote_status_rejects_invalid_transition() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    rate_quote = make_rate_quote(
        tenant_id=tenant_id,
        status=RateQuoteStatus.DRAFT,
    )

    uow.rate_quotes.add(rate_quote)

    with pytest.raises(InvalidRateQuoteStatusTransitionError):
        await TransitionRateQuoteStatus(uow).execute(
            TransitionRateQuoteStatusCommand(
                tenant_id=tenant_id,
                rate_quote_id=rate_quote.id,
                status=RateQuoteStatus.ACCEPTED,
            )
        )

    assert rate_quote.status == RateQuoteStatus.DRAFT

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_transition_rate_quote_status_rejects_unknown_quote() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(RateQuoteNotFoundError):
        await TransitionRateQuoteStatus(uow).execute(
            TransitionRateQuoteStatusCommand(
                tenant_id=uuid4(),
                rate_quote_id=uuid4(),
                status=RateQuoteStatus.QUOTED,
            )
        )

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_transition_rate_quote_status_enforces_tenant_isolation() -> None:
    uow = FakeUnitOfWork()

    rate_quote = make_rate_quote(
        tenant_id=uuid4(),
        status=RateQuoteStatus.DRAFT,
    )

    uow.rate_quotes.add(rate_quote)

    with pytest.raises(RateQuoteNotFoundError):
        await TransitionRateQuoteStatus(uow).execute(
            TransitionRateQuoteStatusCommand(
                tenant_id=uuid4(),
                rate_quote_id=rate_quote.id,
                status=RateQuoteStatus.QUOTED,
            )
        )

    assert rate_quote.status == RateQuoteStatus.DRAFT
    assert uow.rolled_back is True
