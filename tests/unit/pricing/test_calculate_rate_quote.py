from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.pricing.application.exceptions import (
    PricingRuleInactiveError,
    PricingRuleNotEffectiveError,
    PricingRuleNotFoundError,
    PricingRuleServiceMismatchError,
    PricingShipmentNotFoundError,
)
from app.modules.pricing.application.use_cases.calculate_rate_quote import (
    CalculateRateQuote,
    CalculateRateQuoteCommand,
)
from app.modules.pricing.domain.enums import PricingRuleStatus
from app.modules.pricing.infrastructure.models.pricing_rule import PricingRule
from app.modules.rates.domain.enums import RateQuoteStatus
from app.modules.shipments.domain.enums import (
    ServiceType,
    ShipmentStatus,
    WeightUnit,
)
from app.modules.shipments.infrastructure.models.shipment import Shipment
from tests.unit.pricing.fakes import FakeUnitOfWork


def make_shipment(
    *,
    tenant_id: UUID,
    service_type: ServiceType = ServiceType.EXPRESS,
    weight: Decimal = Decimal("10.000"),
    weight_unit: WeightUnit = WeightUnit.KG,
) -> Shipment:
    shipment = Shipment(
        tenant_id=tenant_id,
        customer_id=uuid4(),
        origin_location_id=uuid4(),
        destination_location_id=uuid4(),
        tracking_number=f"PRICING-SHIP-{uuid4()}",
        status=ShipmentStatus.DRAFT,
        service_type=service_type,
        weight=weight,
        weight_unit=weight_unit,
    )
    shipment.id = uuid4()

    return shipment


def make_pricing_rule(
    *,
    tenant_id: UUID,
    service_type: ServiceType = ServiceType.EXPRESS,
    status: PricingRuleStatus = PricingRuleStatus.ACTIVE,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
) -> PricingRule:
    pricing_rule = PricingRule(
        tenant_id=tenant_id,
        name="Express Pricing Rule",
        service_type=service_type,
        currency="USD",
        base_amount=Decimal("25.00"),
        price_per_kg=Decimal("3.5000"),
        surcharge_amount=Decimal("5.00"),
        status=status,
        valid_from=valid_from,
        valid_until=valid_until,
    )
    pricing_rule.id = uuid4()

    return pricing_rule


async def test_calculate_rate_quote_creates_quote_from_pricing_rule() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
        weight=Decimal("10.000"),
        weight_unit=WeightUnit.KG,
    )

    pricing_rule = make_pricing_rule(
        tenant_id=tenant_id,
    )

    uow.shipments.add(shipment)
    uow.pricing_rules.add(pricing_rule)

    result = await CalculateRateQuote(uow).execute(
        CalculateRateQuoteCommand(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
            pricing_rule_id=pricing_rule.id,
        )
    )

    assert result.tenant_id == tenant_id
    assert result.shipment_id == shipment.id

    assert result.currency == "USD"

    assert result.base_amount == Decimal("25.00")

    # 10 KG × 3.50 = 35.00
    # + fixed surcharge 5.00
    assert result.surcharge_amount == Decimal("40.00")

    # 25.00 + 40.00
    assert result.total_amount == Decimal("65.00")

    assert result.status == RateQuoteStatus.DRAFT
    assert result.expires_at is None

    assert len(uow.rate_quotes.items) == 1
    assert uow.rate_quotes.items[0] is result

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.refreshed is True
    assert uow.rolled_back is False


async def test_calculate_rate_quote_converts_lb_to_kg() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
        weight=Decimal("10.000"),
        weight_unit=WeightUnit.LB,
    )

    pricing_rule = make_pricing_rule(
        tenant_id=tenant_id,
    )

    uow.shipments.add(shipment)
    uow.pricing_rules.add(pricing_rule)

    result = await CalculateRateQuote(uow).execute(
        CalculateRateQuoteCommand(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
            pricing_rule_id=pricing_rule.id,
        )
    )

    # 10 lb = 4.5359237 kg
    # × 3.50 = 15.87573295 → 15.88
    # + 5.00 fixed surcharge = 20.88
    assert result.surcharge_amount == Decimal("20.88")

    # 25.00 + 20.88
    assert result.total_amount == Decimal("45.88")


async def test_calculate_rate_quote_uses_rule_valid_until_as_expiration() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    now = datetime.now(UTC)
    valid_until = now + timedelta(days=7)

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    pricing_rule = make_pricing_rule(
        tenant_id=tenant_id,
        valid_from=now - timedelta(days=1),
        valid_until=valid_until,
    )

    uow.shipments.add(shipment)
    uow.pricing_rules.add(pricing_rule)

    result = await CalculateRateQuote(uow).execute(
        CalculateRateQuoteCommand(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
            pricing_rule_id=pricing_rule.id,
        )
    )

    assert result.expires_at == valid_until


async def test_calculate_rate_quote_rejects_unknown_shipment() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    pricing_rule = make_pricing_rule(
        tenant_id=tenant_id,
    )
    uow.pricing_rules.add(pricing_rule)

    with pytest.raises(PricingShipmentNotFoundError):
        await CalculateRateQuote(uow).execute(
            CalculateRateQuoteCommand(
                tenant_id=tenant_id,
                shipment_id=uuid4(),
                pricing_rule_id=pricing_rule.id,
            )
        )

    assert uow.rate_quotes.items == []
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_calculate_rate_quote_rejects_shipment_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=uuid4(),
    )

    pricing_rule = make_pricing_rule(
        tenant_id=tenant_id,
    )

    uow.shipments.add(shipment)
    uow.pricing_rules.add(pricing_rule)

    with pytest.raises(PricingShipmentNotFoundError):
        await CalculateRateQuote(uow).execute(
            CalculateRateQuoteCommand(
                tenant_id=tenant_id,
                shipment_id=shipment.id,
                pricing_rule_id=pricing_rule.id,
            )
        )

    assert uow.rate_quotes.items == []
    assert uow.rolled_back is True


async def test_calculate_rate_quote_rejects_unknown_pricing_rule() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )
    uow.shipments.add(shipment)

    with pytest.raises(PricingRuleNotFoundError):
        await CalculateRateQuote(uow).execute(
            CalculateRateQuoteCommand(
                tenant_id=tenant_id,
                shipment_id=shipment.id,
                pricing_rule_id=uuid4(),
            )
        )

    assert uow.rate_quotes.items == []
    assert uow.rolled_back is True


async def test_calculate_rate_quote_rejects_pricing_rule_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    pricing_rule = make_pricing_rule(
        tenant_id=uuid4(),
    )

    uow.shipments.add(shipment)
    uow.pricing_rules.add(pricing_rule)

    with pytest.raises(PricingRuleNotFoundError):
        await CalculateRateQuote(uow).execute(
            CalculateRateQuoteCommand(
                tenant_id=tenant_id,
                shipment_id=shipment.id,
                pricing_rule_id=pricing_rule.id,
            )
        )

    assert uow.rate_quotes.items == []
    assert uow.rolled_back is True


async def test_calculate_rate_quote_rejects_inactive_rule() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    pricing_rule = make_pricing_rule(
        tenant_id=tenant_id,
        status=PricingRuleStatus.INACTIVE,
    )

    uow.shipments.add(shipment)
    uow.pricing_rules.add(pricing_rule)

    with pytest.raises(PricingRuleInactiveError):
        await CalculateRateQuote(uow).execute(
            CalculateRateQuoteCommand(
                tenant_id=tenant_id,
                shipment_id=shipment.id,
                pricing_rule_id=pricing_rule.id,
            )
        )

    assert uow.rate_quotes.items == []
    assert uow.rolled_back is True


async def test_calculate_rate_quote_rejects_service_mismatch() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
        service_type=ServiceType.STANDARD,
    )

    pricing_rule = make_pricing_rule(
        tenant_id=tenant_id,
        service_type=ServiceType.EXPRESS,
    )

    uow.shipments.add(shipment)
    uow.pricing_rules.add(pricing_rule)

    with pytest.raises(PricingRuleServiceMismatchError):
        await CalculateRateQuote(uow).execute(
            CalculateRateQuoteCommand(
                tenant_id=tenant_id,
                shipment_id=shipment.id,
                pricing_rule_id=pricing_rule.id,
            )
        )

    assert uow.rate_quotes.items == []
    assert uow.rolled_back is True


async def test_calculate_rate_quote_rejects_rule_not_yet_effective() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    pricing_rule = make_pricing_rule(
        tenant_id=tenant_id,
        valid_from=datetime.now(UTC) + timedelta(days=1),
    )

    uow.shipments.add(shipment)
    uow.pricing_rules.add(pricing_rule)

    with pytest.raises(PricingRuleNotEffectiveError):
        await CalculateRateQuote(uow).execute(
            CalculateRateQuoteCommand(
                tenant_id=tenant_id,
                shipment_id=shipment.id,
                pricing_rule_id=pricing_rule.id,
            )
        )

    assert uow.rate_quotes.items == []
    assert uow.rolled_back is True


async def test_calculate_rate_quote_rejects_expired_rule() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    pricing_rule = make_pricing_rule(
        tenant_id=tenant_id,
        valid_until=datetime.now(UTC) - timedelta(seconds=1),
    )

    uow.shipments.add(shipment)
    uow.pricing_rules.add(pricing_rule)

    with pytest.raises(PricingRuleNotEffectiveError):
        await CalculateRateQuote(uow).execute(
            CalculateRateQuoteCommand(
                tenant_id=tenant_id,
                shipment_id=shipment.id,
                pricing_rule_id=pricing_rule.id,
            )
        )

    assert uow.rate_quotes.items == []
    assert uow.rolled_back is True
