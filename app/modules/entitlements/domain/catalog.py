from dataclasses import dataclass

from app.modules.saas.domain.enums import PlanCode


class Entitlements:
    AI_ASSISTANT = "ai.assistant"
    RAG_INDEXING = "ai.rag.indexing"
    OUTBOUND_WEBHOOKS = "notifications.webhooks"
    TEAM_MEMBER_LIMIT = "team.members.max"


@dataclass(frozen=True, slots=True)
class PlanEntitlementSet:
    ai_assistant: bool
    rag_indexing: bool
    outbound_webhooks: bool
    team_member_limit: int | None


PLAN_ENTITLEMENTS: dict[PlanCode, PlanEntitlementSet] = {
    PlanCode.STARTER: PlanEntitlementSet(
        ai_assistant=False,
        rag_indexing=False,
        outbound_webhooks=False,
        team_member_limit=3,
    ),
    PlanCode.PROFESSIONAL: PlanEntitlementSet(
        ai_assistant=True,
        rag_indexing=True,
        outbound_webhooks=True,
        team_member_limit=25,
    ),
    PlanCode.ENTERPRISE: PlanEntitlementSet(
        ai_assistant=True,
        rag_indexing=True,
        outbound_webhooks=True,
        team_member_limit=None,
    ),
}


def get_plan_entitlements(plan_code: PlanCode) -> PlanEntitlementSet:
    return PLAN_ENTITLEMENTS[plan_code]


def is_boolean_entitlement_enabled(
    plan_code: PlanCode,
    entitlement_code: str,
) -> bool:
    entitlements = get_plan_entitlements(plan_code)

    values = {
        Entitlements.AI_ASSISTANT: entitlements.ai_assistant,
        Entitlements.RAG_INDEXING: entitlements.rag_indexing,
        Entitlements.OUTBOUND_WEBHOOKS: entitlements.outbound_webhooks,
    }

    try:
        return values[entitlement_code]
    except KeyError as exc:
        raise ValueError(f"Unknown boolean entitlement: {entitlement_code}") from exc
