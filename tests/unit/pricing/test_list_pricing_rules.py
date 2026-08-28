from decimal import Decimal
from uuid import UUID, uuid4

from app.modules.pricing.application.use_cases.list_pricing_rules import (
    ListPricingRules,
    ListPricingRulesQuery,
)
from app.modules.pricing.domain.enums import PricingRuleStatus
from app.modules.pricing.infrastructure.models.pricing_rule import PricingRule
from app.modules.shipments.domain.enums import ServiceType
from tests.unit.pricing.fakes import FakeUnitOfWork


def make_pricing_rule(
    *,
    tenant_id: UUID,
    name: str,
) -> PricingRule:
    pricing_rule = PricingRule(
        tenant_id=tenant_id,
        name=name,
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


async def test_list_pricing_rules_returns_tenant_rules() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    first = make_pricing_rule(
        tenant_id=tenant_id,
        name="First Rule",
    )

    second = make_pricing_rule(
        tenant_id=tenant_id,
        name="Second Rule",
    )

    uow.pricing_rules.add(first)
    uow.pricing_rules.add(second)

    result = await ListPricingRules(uow).execute(
        ListPricingRulesQuery(
            tenant_id=tenant_id,
        )
    )

    assert result == [
        first,
        second,
    ]


async def test_list_pricing_rules_excludes_other_tenants() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    expected = make_pricing_rule(
        tenant_id=tenant_id,
        name="Expected Rule",
    )

    foreign = make_pricing_rule(
        tenant_id=uuid4(),
        name="Foreign Rule",
    )

    uow.pricing_rules.add(expected)
    uow.pricing_rules.add(foreign)

    result = await ListPricingRules(uow).execute(
        ListPricingRulesQuery(
            tenant_id=tenant_id,
        )
    )

    assert result == [expected]


async def test_list_pricing_rules_returns_empty_list() -> None:
    uow = FakeUnitOfWork()

    result = await ListPricingRules(uow).execute(
        ListPricingRulesQuery(
            tenant_id=uuid4(),
        )
    )

    assert result == []
