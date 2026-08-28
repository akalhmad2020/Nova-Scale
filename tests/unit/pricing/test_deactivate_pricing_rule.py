from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.pricing.application.exceptions import (
    PricingRuleAlreadyInactiveError,
    PricingRuleNotFoundError,
)
from app.modules.pricing.application.use_cases.deactivate_pricing_rule import (
    DeactivatePricingRule,
    DeactivatePricingRuleCommand,
)
from app.modules.pricing.domain.enums import PricingRuleStatus
from app.modules.pricing.infrastructure.models.pricing_rule import PricingRule
from app.modules.shipments.domain.enums import ServiceType
from tests.unit.pricing.fakes import FakeUnitOfWork


def make_pricing_rule(
    *,
    status: PricingRuleStatus = PricingRuleStatus.ACTIVE,
) -> PricingRule:
    pricing_rule = PricingRule(
        tenant_id=uuid4(),
        name="Pricing Rule",
        service_type=ServiceType.STANDARD,
        currency="USD",
        base_amount=Decimal("10.00"),
        price_per_kg=Decimal("2.0000"),
        surcharge_amount=Decimal("1.00"),
        status=status,
    )
    pricing_rule.id = uuid4()

    return pricing_rule


async def test_deactivate_pricing_rule() -> None:
    uow = FakeUnitOfWork()
    pricing_rule = make_pricing_rule()

    uow.pricing_rules.add(pricing_rule)

    result = await DeactivatePricingRule(uow).execute(
        DeactivatePricingRuleCommand(
            tenant_id=pricing_rule.tenant_id,
            pricing_rule_id=pricing_rule.id,
        )
    )

    assert result is pricing_rule
    assert result.status == PricingRuleStatus.INACTIVE

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.refreshed is True
    assert uow.rolled_back is False


async def test_deactivate_pricing_rule_rejects_already_inactive_rule() -> None:
    uow = FakeUnitOfWork()
    pricing_rule = make_pricing_rule(
        status=PricingRuleStatus.INACTIVE,
    )

    uow.pricing_rules.add(pricing_rule)

    with pytest.raises(PricingRuleAlreadyInactiveError):
        await DeactivatePricingRule(uow).execute(
            DeactivatePricingRuleCommand(
                tenant_id=pricing_rule.tenant_id,
                pricing_rule_id=pricing_rule.id,
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_deactivate_pricing_rule_rejects_unknown_rule() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(PricingRuleNotFoundError):
        await DeactivatePricingRule(uow).execute(
            DeactivatePricingRuleCommand(
                tenant_id=uuid4(),
                pricing_rule_id=uuid4(),
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_deactivate_pricing_rule_enforces_tenant_isolation() -> None:
    uow = FakeUnitOfWork()
    pricing_rule = make_pricing_rule()

    uow.pricing_rules.add(pricing_rule)

    with pytest.raises(PricingRuleNotFoundError):
        await DeactivatePricingRule(uow).execute(
            DeactivatePricingRuleCommand(
                tenant_id=uuid4(),
                pricing_rule_id=pricing_rule.id,
            )
        )

    assert pricing_rule.status == PricingRuleStatus.ACTIVE
    assert uow.committed is False
    assert uow.rolled_back is True
