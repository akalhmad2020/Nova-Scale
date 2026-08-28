from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.pricing.application.exceptions import (
    PricingRuleNotFoundError,
)
from app.modules.pricing.application.use_cases.get_pricing_rule import (
    GetPricingRule,
    GetPricingRuleQuery,
)
from app.modules.pricing.domain.enums import PricingRuleStatus
from app.modules.pricing.infrastructure.models.pricing_rule import PricingRule
from app.modules.shipments.domain.enums import ServiceType
from tests.unit.pricing.fakes import FakeUnitOfWork


def make_pricing_rule(
    *,
    tenant_id: UUID,
) -> PricingRule:
    pricing_rule = PricingRule(
        tenant_id=tenant_id,
        name="Standard Rule",
        service_type=ServiceType.STANDARD,
        currency="USD",
        base_amount=Decimal("20.00"),
        price_per_kg=Decimal("2.5000"),
        surcharge_amount=Decimal("5.00"),
        status=PricingRuleStatus.ACTIVE,
        valid_from=None,
        valid_until=None,
    )
    pricing_rule.id = uuid4()

    return pricing_rule


async def test_get_pricing_rule_returns_rule() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    pricing_rule = make_pricing_rule(
        tenant_id=tenant_id,
    )

    uow.pricing_rules.add(pricing_rule)

    result = await GetPricingRule(uow).execute(
        GetPricingRuleQuery(
            tenant_id=tenant_id,
            pricing_rule_id=pricing_rule.id,
        )
    )

    assert result is pricing_rule


async def test_get_pricing_rule_rejects_unknown_rule() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(PricingRuleNotFoundError):
        await GetPricingRule(uow).execute(
            GetPricingRuleQuery(
                tenant_id=uuid4(),
                pricing_rule_id=uuid4(),
            )
        )

    assert uow.rolled_back is True


async def test_get_pricing_rule_enforces_tenant_isolation() -> None:
    uow = FakeUnitOfWork()

    pricing_rule = make_pricing_rule(
        tenant_id=uuid4(),
    )
    uow.pricing_rules.add(pricing_rule)

    with pytest.raises(PricingRuleNotFoundError):
        await GetPricingRule(uow).execute(
            GetPricingRuleQuery(
                tenant_id=uuid4(),
                pricing_rule_id=pricing_rule.id,
            )
        )

    assert uow.rolled_back is True
