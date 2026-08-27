from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.rates.application.exceptions import (
    RateQuoteShipmentNotFoundError,
)
from app.modules.rates.application.use_cases.create_rate_quote import (
    CreateRateQuote,
    CreateRateQuoteCommand,
)
from app.modules.rates.domain.enums import RateQuoteStatus
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
) -> Shipment:
    shipment = Shipment(
        tenant_id=tenant_id,
        customer_id=uuid4(),
        origin_location_id=uuid4(),
        destination_location_id=uuid4(),
        tracking_number="RATE-SHIP-001",
        status=ShipmentStatus.DRAFT,
        service_type=ServiceType.STANDARD,
        weight=Decimal("10.000"),
        weight_unit=WeightUnit.KG,
    )
    shipment.id = uuid4()

    return shipment


async def test_create_rate_quote_creates_draft_quote() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )
    uow.shipments.add(shipment)

    expires_at = datetime.now(UTC) + timedelta(hours=1)

    result = await CreateRateQuote(uow).execute(
        CreateRateQuoteCommand(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
            currency="usd",
            base_amount=Decimal("100.00"),
            surcharge_amount=Decimal("15.50"),
            expires_at=expires_at,
        )
    )

    assert result.tenant_id == tenant_id
    assert result.shipment_id == shipment.id

    assert result.currency == "USD"
    assert result.base_amount == Decimal("100.00")
    assert result.surcharge_amount == Decimal("15.50")
    assert result.total_amount == Decimal("115.50")

    assert result.status == RateQuoteStatus.DRAFT
    assert result.expires_at == expires_at

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.refreshed is True
    assert uow.rolled_back is False


async def test_create_rate_quote_normalizes_currency() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )
    uow.shipments.add(shipment)

    result = await CreateRateQuote(uow).execute(
        CreateRateQuoteCommand(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
            currency="  eur  ",
            base_amount=Decimal("50.00"),
            surcharge_amount=Decimal("5.00"),
        )
    )

    assert result.currency == "EUR"


async def test_create_rate_quote_calculates_total_amount() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )
    uow.shipments.add(shipment)

    result = await CreateRateQuote(uow).execute(
        CreateRateQuoteCommand(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
            currency="USD",
            base_amount=Decimal("123.45"),
            surcharge_amount=Decimal("6.55"),
        )
    )

    assert result.total_amount == Decimal("130.00")


async def test_create_rate_quote_rejects_unknown_shipment() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(RateQuoteShipmentNotFoundError):
        await CreateRateQuote(uow).execute(
            CreateRateQuoteCommand(
                tenant_id=uuid4(),
                shipment_id=uuid4(),
                currency="USD",
                base_amount=Decimal("100.00"),
                surcharge_amount=Decimal("10.00"),
            )
        )

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_create_rate_quote_rejects_shipment_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    shipment = make_shipment(
        tenant_id=uuid4(),
    )
    uow.shipments.add(shipment)

    with pytest.raises(RateQuoteShipmentNotFoundError):
        await CreateRateQuote(uow).execute(
            CreateRateQuoteCommand(
                tenant_id=uuid4(),
                shipment_id=shipment.id,
                currency="USD",
                base_amount=Decimal("100.00"),
                surcharge_amount=Decimal("10.00"),
            )
        )

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True
