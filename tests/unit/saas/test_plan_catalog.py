from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from app.main import app
from app.modules.saas.api.schemas import PlanResponse
from app.modules.saas.domain.enums import PlanCode


def test_plan_catalog_is_public_and_exposes_entitlements() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/plans")

    assert response.status_code == 200

    plans = TypeAdapter(list[PlanResponse]).validate_json(response.content)

    assert [plan.code for plan in plans] == [
        PlanCode.STARTER,
        PlanCode.PROFESSIONAL,
        PlanCode.ENTERPRISE,
    ]

    starter, professional, enterprise = plans

    assert starter.entitlements.ai_assistant is False
    assert starter.entitlements.rag_indexing is False
    assert starter.entitlements.team_member_limit == 3

    assert professional.recommended is True
    assert professional.entitlements.ai_assistant is True
    assert professional.entitlements.rag_indexing is True
    assert professional.entitlements.outbound_webhooks is True
    assert professional.entitlements.team_member_limit == 25

    assert enterprise.entitlements.ai_assistant is True
    assert enterprise.entitlements.team_member_limit is None
