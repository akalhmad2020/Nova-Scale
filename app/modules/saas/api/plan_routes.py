from fastapi import APIRouter

from app.modules.entitlements.domain.catalog import get_plan_entitlements
from app.modules.saas.api.schemas import PlanEntitlementsResponse, PlanResponse
from app.modules.saas.domain.catalog import list_plan_definitions

router = APIRouter(
    prefix="/plans",
    tags=["saas-plans"],
)


@router.get("", response_model=list[PlanResponse])
def list_plans() -> list[PlanResponse]:
    responses: list[PlanResponse] = []

    for plan in list_plan_definitions():
        entitlements = get_plan_entitlements(plan.code)
        responses.append(
            PlanResponse(
                code=plan.code,
                name=plan.name,
                description=plan.description,
                display_order=plan.display_order,
                recommended=plan.recommended,
                self_service=plan.self_service,
                entitlements=PlanEntitlementsResponse(
                    ai_assistant=entitlements.ai_assistant,
                    rag_indexing=entitlements.rag_indexing,
                    outbound_webhooks=entitlements.outbound_webhooks,
                    team_member_limit=entitlements.team_member_limit,
                ),
            )
        )

    return responses
