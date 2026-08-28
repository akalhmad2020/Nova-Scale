from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.pricing.application.exceptions import (
    PricingRuleNotFoundError,
)
from app.modules.pricing.application.use_cases.update_pricing_rule import (
    UpdatePricingRule,
    UpdatePricingRuleCommand,
)
from app.modules.pricing.domain.enums import PricingRuleStatus
from app.modules.pricing.infrastructure.models.pricing_rule import PricingRule
from app.modules.shipments.domain.enums import ServiceType
from tests.unit.pricing.fakes import FakeUnitOfWork


def make_pricing_rule() -> PricingRule:
    pricing_rule = PricingRule(
        tenant_id=uuid4(),
        name="Old Rule",
        service_type=ServiceType.STANDARD,
        currency="USD",
        base_amount=Decimal("10.00"),
        price_per_kg=Decimal("2.0000"),
        surcharge_amount=Decimal("1.00"),
        status=PricingRuleStatus.ACTIVE,
    )
    pricing_rule.id = uuid4()

    return pricing_rule


async def test_update_pricing_rule_updates_requested_fields() -> None:
    uow = FakeUnitOfWork()
    pricing_rule = make_pricing_rule()

    uow.pricing_rules.add(pricing_rule)

    result = await UpdatePricingRule(uow).execute(
        UpdatePricingRuleCommand(
            tenant_id=pricing_rule.tenant_id,
            pricing_rule_id=pricing_rule.id,
            name="  Express Rule  ",
            service_type=ServiceType.EXPRESS,
            currency=" eur ",
            base_amount=Decimal("25.00"),
            price_per_kg=Decimal("3.5000"),
            surcharge_amount=Decimal("5.00"),
        )
    )

    assert result is pricing_rule
    assert result.name == "Express Rule"
    assert result.service_type == ServiceType.EXPRESS
    assert result.currency == "EUR"
    assert result.base_amount == Decimal("25.00")
    assert result.price_per_kg == Decimal("3.5000")
    assert result.surcharge_amount == Decimal("5.00")

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.refreshed is True
    assert uow.rolled_back is False


async def test_update_pricing_rule_keeps_unspecified_fields() -> None:
    uow = FakeUnitOfWork()
    pricing_rule = make_pricing_rule()

    uow.pricing_rules.add(pricing_rule)

    result = await UpdatePricingRule(uow).execute(
        UpdatePricingRuleCommand(
            tenant_id=pricing_rule.tenant_id,
            pricing_rule_id=pricing_rule.id,
            name="Updated Name",
        )
    )

    assert result.name == "Updated Name"
    assert result.service_type == ServiceType.STANDARD
    assert result.currency == "USD"
    assert result.base_amount == Decimal("10.00")
    assert result.price_per_kg == Decimal("2.0000")
    assert result.surcharge_amount == Decimal("1.00")


async def test_update_pricing_rule_rejects_unknown_rule() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(PricingRuleNotFoundError):
        await UpdatePricingRule(uow).execute(
            UpdatePricingRuleCommand(
                tenant_id=uuid4(),
                pricing_rule_id=uuid4(),
                name="Updated",
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_update_pricing_rule_enforces_tenant_isolation() -> None:
    uow = FakeUnitOfWork()
    pricing_rule = make_pricing_rule()

    uow.pricing_rules.add(pricing_rule)

    with pytest.raises(PricingRuleNotFoundError):
        await UpdatePricingRule(uow).execute(
            UpdatePricingRuleCommand(
                tenant_id=uuid4(),
                pricing_rule_id=pricing_rule.id,
                name="Should Not Update",
            )
        )

    assert pricing_rule.name == "Old Rule"
    assert uow.committed is False
    assert uow.rolled_back is True
