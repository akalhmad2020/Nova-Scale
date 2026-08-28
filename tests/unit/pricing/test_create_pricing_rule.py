from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from app.modules.pricing.application.use_cases.create_pricing_rule import (
    CreatePricingRule,
    CreatePricingRuleCommand,
)
from app.modules.pricing.domain.enums import PricingRuleStatus
from app.modules.shipments.domain.enums import ServiceType
from tests.unit.pricing.fakes import FakeUnitOfWork


async def test_create_pricing_rule_creates_active_rule() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()
    valid_from = datetime.now(UTC)
    valid_until = valid_from + timedelta(days=30)

    result = await CreatePricingRule(uow).execute(
        CreatePricingRuleCommand(
            tenant_id=tenant_id,
            name="  Express Palestine  ",
            service_type=ServiceType.EXPRESS,
            currency=" usd ",
            base_amount=Decimal("25.00"),
            price_per_kg=Decimal("3.5000"),
            surcharge_amount=Decimal("5.00"),
            valid_from=valid_from,
            valid_until=valid_until,
        )
    )

    assert result.tenant_id == tenant_id
    assert result.name == "Express Palestine"
    assert result.service_type == ServiceType.EXPRESS
    assert result.currency == "USD"

    assert result.base_amount == Decimal("25.00")
    assert result.price_per_kg == Decimal("3.5000")
    assert result.surcharge_amount == Decimal("5.00")

    assert result.status == PricingRuleStatus.ACTIVE
    assert result.valid_from == valid_from
    assert result.valid_until == valid_until

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.refreshed is True
    assert uow.rolled_back is False


async def test_create_pricing_rule_allows_open_validity_range() -> None:
    uow = FakeUnitOfWork()

    result = await CreatePricingRule(uow).execute(
        CreatePricingRuleCommand(
            tenant_id=uuid4(),
            name="Standard Rule",
            service_type=ServiceType.STANDARD,
            currency="EUR",
            base_amount=Decimal("10.00"),
            price_per_kg=Decimal("2.0000"),
            surcharge_amount=Decimal("0.00"),
        )
    )

    assert result.valid_from is None
    assert result.valid_until is None
