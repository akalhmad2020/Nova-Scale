from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.rates.application.exceptions import RateQuoteNotFoundError
from app.modules.rates.application.use_cases.get_rate_quote import (
    GetRateQuote,
    GetRateQuoteQuery,
)
from app.modules.rates.domain.enums import RateQuoteStatus
from app.modules.rates.infrastructure.models.rate_quote import RateQuote
from tests.unit.rates.fakes import FakeUnitOfWork


def make_rate_quote(
    *,
    tenant_id: UUID,
    shipment_id: UUID,
) -> RateQuote:
    rate_quote = RateQuote(
        tenant_id=tenant_id,
        shipment_id=shipment_id,
        currency="USD",
        base_amount=Decimal("100.00"),
        surcharge_amount=Decimal("10.00"),
        total_amount=Decimal("110.00"),
        status=RateQuoteStatus.DRAFT,
        expires_at=None,
    )
    rate_quote.id = uuid4()

    return rate_quote


async def test_get_rate_quote_returns_quote() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    rate_quote = make_rate_quote(
        tenant_id=tenant_id,
        shipment_id=uuid4(),
    )
    uow.rate_quotes.add(rate_quote)

    result = await GetRateQuote(uow).execute(
        GetRateQuoteQuery(
            tenant_id=tenant_id,
            rate_quote_id=rate_quote.id,
        )
    )

    assert result is rate_quote


async def test_get_rate_quote_rejects_unknown_quote() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(RateQuoteNotFoundError):
        await GetRateQuote(uow).execute(
            GetRateQuoteQuery(
                tenant_id=uuid4(),
                rate_quote_id=uuid4(),
            )
        )

    assert uow.rolled_back is True


async def test_get_rate_quote_rejects_quote_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    rate_quote = make_rate_quote(
        tenant_id=uuid4(),
        shipment_id=uuid4(),
    )
    uow.rate_quotes.add(rate_quote)

    with pytest.raises(RateQuoteNotFoundError):
        await GetRateQuote(uow).execute(
            GetRateQuoteQuery(
                tenant_id=uuid4(),
                rate_quote_id=rate_quote.id,
            )
        )

    assert uow.rolled_back is True
