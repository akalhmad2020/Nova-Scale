from app.core.database import SessionFactory
from app.modules.pricing.application.use_cases.calculate_rate_quote import (
    CalculateRateQuote,
)
from app.modules.pricing.application.use_cases.create_pricing_rule import (
    CreatePricingRule,
)
from app.modules.pricing.application.use_cases.deactivate_pricing_rule import (
    DeactivatePricingRule,
)
from app.modules.pricing.application.use_cases.get_pricing_rule import (
    GetPricingRule,
)
from app.modules.pricing.application.use_cases.list_pricing_rules import (
    ListPricingRules,
)
from app.modules.pricing.application.use_cases.update_pricing_rule import (
    UpdatePricingRule,
)
from app.modules.pricing.infrastructure.unit_of_work import (
    SQLAlchemyUnitOfWork,
)


def get_create_pricing_rule_use_case() -> CreatePricingRule:
    return CreatePricingRule(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_get_pricing_rule_use_case() -> GetPricingRule:
    return GetPricingRule(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_list_pricing_rules_use_case() -> ListPricingRules:
    return ListPricingRules(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_update_pricing_rule_use_case() -> UpdatePricingRule:
    return UpdatePricingRule(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_deactivate_pricing_rule_use_case() -> DeactivatePricingRule:
    return DeactivatePricingRule(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_calculate_rate_quote_use_case() -> CalculateRateQuote:
    return CalculateRateQuote(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )
