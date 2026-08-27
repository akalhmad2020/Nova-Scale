from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.rates.application.exceptions import (
    RateQuoteShipmentNotFoundError,
)
from app.modules.rates.application.use_cases.list_rate_quotes import (
    ListRateQuotes,
    ListRateQuotesQuery,
)
from app.modules.rates.domain.enums import RateQuoteStatus
from app.modules.rates.infrastructure.models.rate_quote import RateQuote
from app.modules.shipments.domain.enums import (
    ServiceType,
    ShipmentStatus,
    WeightUnit,
)
from app.modules.shipments.infrastructure.models.shipment import Shipment
from tests.unit.rates.fakes import FakeUnitOfWork


def make_shipment(
    *,
    tenant_id: UUID,
    tracking_number: str,
) -> Shipment:
    shipment = Shipment(
        tenant_id=tenant_id,
        customer_id=uuid4(),
        origin_location_id=uuid4(),
        destination_location_id=uuid4(),
        tracking_number=tracking_number,
        status=ShipmentStatus.DRAFT,
        service_type=ServiceType.STANDARD,
        weight=Decimal("10.000"),
        weight_unit=WeightUnit.KG,
    )
    shipment.id = uuid4()

    return shipment


def make_rate_quote(
    *,
    tenant_id: UUID,
    shipment_id: UUID,
    amount: str,
) -> RateQuote:
    base_amount = Decimal(amount)
    surcharge_amount = Decimal("10.00")

    rate_quote = RateQuote(
        tenant_id=tenant_id,
        shipment_id=shipment_id,
        currency="USD",
        base_amount=base_amount,
        surcharge_amount=surcharge_amount,
        total_amount=base_amount + surcharge_amount,
        status=RateQuoteStatus.DRAFT,
        expires_at=None,
    )
    rate_quote.id = uuid4()

    return rate_quote


async def test_list_rate_quotes_returns_shipment_quotes() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="RATE-SHIP-001",
    )

    first = make_rate_quote(
        tenant_id=tenant_id,
        shipment_id=shipment.id,
        amount="100.00",
    )

    second = make_rate_quote(
        tenant_id=tenant_id,
        shipment_id=shipment.id,
        amount="200.00",
    )

    uow.shipments.add(shipment)
    uow.rate_quotes.add(first)
    uow.rate_quotes.add(second)

    result = await ListRateQuotes(uow).execute(
        ListRateQuotesQuery(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
        )
    )

    assert result == [
        first,
        second,
    ]


async def test_list_rate_quotes_excludes_other_shipments() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="RATE-SHIP-001",
    )

    other_shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="RATE-SHIP-002",
    )

    expected = make_rate_quote(
        tenant_id=tenant_id,
        shipment_id=shipment.id,
        amount="100.00",
    )

    other = make_rate_quote(
        tenant_id=tenant_id,
        shipment_id=other_shipment.id,
        amount="200.00",
    )

    uow.shipments.add(shipment)
    uow.shipments.add(other_shipment)

    uow.rate_quotes.add(expected)
    uow.rate_quotes.add(other)

    result = await ListRateQuotes(uow).execute(
        ListRateQuotesQuery(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
        )
    )

    assert result == [expected]


async def test_list_rate_quotes_returns_empty_list() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="RATE-SHIP-001",
    )

    uow.shipments.add(shipment)

    result = await ListRateQuotes(uow).execute(
        ListRateQuotesQuery(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
        )
    )

    assert result == []


async def test_list_rate_quotes_rejects_unknown_shipment() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(RateQuoteShipmentNotFoundError):
        await ListRateQuotes(uow).execute(
            ListRateQuotesQuery(
                tenant_id=uuid4(),
                shipment_id=uuid4(),
            )
        )

    assert uow.rolled_back is True


async def test_list_rate_quotes_rejects_shipment_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    shipment = make_shipment(
        tenant_id=uuid4(),
        tracking_number="RATE-SHIP-001",
    )
    uow.shipments.add(shipment)

    with pytest.raises(RateQuoteShipmentNotFoundError):
        await ListRateQuotes(uow).execute(
            ListRateQuotesQuery(
                tenant_id=uuid4(),
                shipment_id=shipment.id,
            )
        )

    assert uow.rolled_back is True
