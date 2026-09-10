from datetime import timedelta
from uuid import UUID

from fastapi.testclient import TestClient

from app.ai.application.agent.shipment_operational_models import (
    ShipmentOperationalAnalysis,
    ShipmentOperationalIssue,
)
from app.ai.application.agent.shipment_resolution_exceptions import (
    ShipmentIdentifierAmbiguousError,
)
from app.ai.application.agent.shipment_resolution_models import ResolvedShipment
from app.ai.application.services.answer_question import AnswerQuestionService
from app.ai.domain.rag_models import (
    DocumentChunk,
    RAGAnswer,
    RetrievedChunk,
)
from app.api.routes.ai import (
    get_analyze_shipment_service,
    get_answer_question_service,
    get_resolve_shipment_service,
)
from app.main import app
from app.modules.entitlements.api.dependencies import get_entitlements_use_case
from app.modules.identity.api.auth_dependencies import get_current_membership
from app.modules.identity.api.dependencies import get_check_permission_use_case
from app.modules.shipments.application.exceptions import ShipmentNotFoundError

TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
SHIPMENT_ID = UUID("33333333-3333-3333-3333-333333333333")


class FakeMembership:
    def __init__(
        self,
        tenant_id: UUID,
    ) -> None:
        self.tenant_id = tenant_id
        self.role_id = UUID("22222222-2222-2222-2222-222222222222")


class FakeEntitlementSnapshot:
    def is_enabled(
        self,
        entitlement_code: str,
    ) -> bool:
        return True


class FakeEntitlementsUseCase:
    async def execute(
        self,
        tenant_id: UUID,
    ) -> FakeEntitlementSnapshot:
        return FakeEntitlementSnapshot()


class FakeCheckPermissionUseCase:
    async def execute(
        self,
        query: object,
    ) -> None:
        return None


class FakeAnswerQuestionService(AnswerQuestionService):
    def __init__(self) -> None:
        pass

    async def execute(
        self,
        *,
        tenant_id: UUID,
        question: str,
        limit: int = 5,
    ) -> RAGAnswer:
        return RAGAnswer(
            content="Shipment NOVA-100 is in transit.",
            model="fake-model",
            sources=(
                RetrievedChunk(
                    chunk=DocumentChunk(
                        id="document-1:0",
                        document_id="document-1",
                        content="Shipment NOVA-100 is currently in transit.",
                        chunk_index=0,
                    ),
                    score=0.95,
                ),
            ),
        )


class FakeResolveShipmentService:
    async def execute(
        self,
        *,
        tenant_id: UUID,
        identifier: str,
    ) -> ResolvedShipment:
        del tenant_id

        if identifier == "missing-shipment":
            raise ShipmentNotFoundError

        if identifier == "duplicate-reference":
            raise ShipmentIdentifierAmbiguousError

        return ResolvedShipment(
            shipment_id=SHIPMENT_ID,
            identifier=identifier,
            identifier_kind=("uuid" if identifier == str(SHIPMENT_ID) else "tracking_number"),
        )


class FakeAnalyzeShipmentService:
    async def execute(
        self,
        *,
        tenant_id: UUID,
        shipment_id: UUID,
    ) -> ShipmentOperationalAnalysis:
        assert tenant_id == TENANT_ID
        assert shipment_id == SHIPMENT_ID

        return ShipmentOperationalAnalysis(
            issues=(
                ShipmentOperationalIssue(
                    code="stale_in_transit",
                    severity="warning",
                    message=(
                        "Shipment is in transit but has not received a recent operational event."
                    ),
                    recommended_action=(
                        "Verify the shipment's current location and contact "
                        "the carrier if no recent tracking update is available."
                    ),
                    age=timedelta(hours=30),
                ),
            ),
        )


def override_current_membership() -> FakeMembership:
    return FakeMembership(
        tenant_id=TENANT_ID,
    )


def configure_dependency_overrides() -> None:
    app.dependency_overrides[get_current_membership] = override_current_membership
    app.dependency_overrides[get_entitlements_use_case] = lambda: FakeEntitlementsUseCase()
    app.dependency_overrides[get_check_permission_use_case] = lambda: FakeCheckPermissionUseCase()
    app.dependency_overrides[get_answer_question_service] = lambda: FakeAnswerQuestionService()
    app.dependency_overrides[get_resolve_shipment_service] = lambda: FakeResolveShipmentService()
    app.dependency_overrides[get_analyze_shipment_service] = lambda: FakeAnalyzeShipmentService()


def test_ask_question_endpoint() -> None:
    configure_dependency_overrides()

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/ai/tenants/{TENANT_ID}/ask",
            json={
                "question": "What is the status of shipment NOVA-100?",
                "limit": 5,
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "content": "Shipment NOVA-100 is in transit.",
            "model": "fake-model",
            "sources": [
                {
                    "chunk_id": "document-1:0",
                    "document_id": "document-1",
                    "chunk_index": 0,
                    "content": "Shipment NOVA-100 is currently in transit.",
                    "score": 0.95,
                }
            ],
        }
    finally:
        app.dependency_overrides.clear()


def test_ask_question_endpoint_rejects_empty_question() -> None:
    configure_dependency_overrides()

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/ai/tenants/{TENANT_ID}/ask",
            json={
                "question": "",
            },
        )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_ask_question_endpoint_rejects_invalid_limit() -> None:
    configure_dependency_overrides()

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/ai/tenants/{TENANT_ID}/ask",
            json={
                "question": "Where is my shipment?",
                "limit": 0,
            },
        )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_ask_question_endpoint_rejects_invalid_tenant_id() -> None:
    configure_dependency_overrides()

    try:
        client = TestClient(app)

        response = client.post(
            "/api/v1/ai/tenants/not-a-valid-uuid/ask",
            json={
                "question": "Where is my shipment?",
            },
        )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_shipment_operational_analysis_endpoint_returns_structured_analysis() -> None:
    configure_dependency_overrides()

    try:
        client = TestClient(app)

        response = client.get(f"/api/v1/ai/tenants/{TENANT_ID}/shipments/SHIP-001/operations")

        assert response.status_code == 200
        assert response.json() == {
            "shipment_id": str(SHIPMENT_ID),
            "identifier": "SHIP-001",
            "identifier_kind": "tracking_number",
            "has_issues": True,
            "highest_severity": "warning",
            "risk_score": 25,
            "risk_level": "medium",
            "issues": [
                {
                    "code": "stale_in_transit",
                    "severity": "warning",
                    "message": (
                        "Shipment is in transit but has not received a recent operational event."
                    ),
                    "recommended_action": (
                        "Verify the shipment's current location and contact "
                        "the carrier if no recent tracking update is available."
                    ),
                    "age_seconds": 108000,
                }
            ],
        }
    finally:
        app.dependency_overrides.clear()


def test_shipment_operational_analysis_endpoint_returns_not_found() -> None:
    configure_dependency_overrides()

    try:
        client = TestClient(app)

        response = client.get(
            f"/api/v1/ai/tenants/{TENANT_ID}/shipments/missing-shipment/operations"
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Shipment not found",
        }
    finally:
        app.dependency_overrides.clear()


def test_shipment_operational_analysis_endpoint_returns_conflict_for_ambiguous_identifier() -> None:
    configure_dependency_overrides()

    try:
        client = TestClient(app)

        response = client.get(
            f"/api/v1/ai/tenants/{TENANT_ID}/shipments/duplicate-reference/operations"
        )

        assert response.status_code == 409
        assert response.json() == {
            "detail": "Shipment identifier matches multiple shipments",
        }
    finally:
        app.dependency_overrides.clear()
