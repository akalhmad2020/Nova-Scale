from dataclasses import dataclass

from app.modules.saas.domain.enums import PlanCode


@dataclass(frozen=True, slots=True)
class PlanDefinition:
    code: PlanCode
    name: str
    description: str
    display_order: int
    recommended: bool = False


PLAN_CATALOG: tuple[PlanDefinition, ...] = (
    PlanDefinition(
        code=PlanCode.STARTER,
        name="Starter",
        description="Core shipping operations for small teams getting started.",
        display_order=10,
    ),
    PlanDefinition(
        code=PlanCode.PROFESSIONAL,
        name="Professional",
        description="AI-assisted logistics operations for growing teams.",
        display_order=20,
        recommended=True,
    ),
    PlanDefinition(
        code=PlanCode.ENTERPRISE,
        name="Enterprise",
        description="Advanced controls and scale for complex logistics organizations.",
        display_order=30,
    ),
)


def list_plan_definitions() -> tuple[PlanDefinition, ...]:
    return PLAN_CATALOG
