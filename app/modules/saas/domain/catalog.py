from dataclasses import dataclass

from app.modules.saas.domain.enums import PlanCode


@dataclass(frozen=True, slots=True)
class PlanDefinition:
    code: PlanCode
    name: str
    description: str
    display_order: int
    recommended: bool = False
    self_service: bool = False


PLAN_CATALOG: tuple[PlanDefinition, ...] = (
    PlanDefinition(
        code=PlanCode.STARTER,
        name="Starter",
        description="Core shipping operations for small teams getting started.",
        display_order=10,
        self_service=True,
    ),
    PlanDefinition(
        code=PlanCode.PROFESSIONAL,
        name="Professional",
        description="AI-assisted logistics operations for growing teams.",
        display_order=20,
        recommended=True,
        self_service=True,
    ),
    PlanDefinition(
        code=PlanCode.ENTERPRISE,
        name="Enterprise",
        description="Advanced controls and scale for complex logistics organizations.",
        display_order=30,
        self_service=False,
    ),
)


def list_plan_definitions() -> tuple[PlanDefinition, ...]:
    return PLAN_CATALOG


def get_plan_definition(plan_code: PlanCode) -> PlanDefinition:
    for definition in PLAN_CATALOG:
        if definition.code is plan_code:
            return definition

    raise ValueError(f"Unknown plan code: {plan_code}")


def is_self_service_plan(plan_code: PlanCode) -> bool:
    return get_plan_definition(plan_code).self_service
