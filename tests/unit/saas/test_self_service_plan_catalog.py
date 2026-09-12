from app.modules.saas.domain.catalog import get_plan_definition
from app.modules.saas.domain.enums import PlanCode


def test_starter_and_professional_are_self_service() -> None:
    assert get_plan_definition(PlanCode.STARTER).self_service is True
    assert get_plan_definition(PlanCode.PROFESSIONAL).self_service is True


def test_enterprise_is_sales_assisted() -> None:
    assert get_plan_definition(PlanCode.ENTERPRISE).self_service is False
