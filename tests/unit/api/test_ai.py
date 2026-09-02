from uuid import UUID

from fastapi.testclient import TestClient

from app.ai.application.services.answer_question import AnswerQuestionService
from app.ai.domain.rag_models import (
    DocumentChunk,
    RAGAnswer,
    RetrievedChunk,
)
from app.api.routes.ai import get_answer_question_service
from app.main import app
from app.modules.identity.api.auth_dependencies import get_current_membership


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


def test_ask_question_endpoint() -> None:
    app.dependency_overrides[get_answer_question_service] = lambda: FakeAnswerQuestionService()
    app.dependency_overrides[get_current_membership] = lambda: object()

    try:
        client = TestClient(app)

        response = client.post(
            "/api/v1/ai/tenants/11111111-1111-1111-1111-111111111111/ask",
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
    app.dependency_overrides[get_current_membership] = lambda: object()

    try:
        client = TestClient(app)

        response = client.post(
            "/api/v1/ai/tenants/11111111-1111-1111-1111-111111111111/ask",
            json={
                "question": "",
            },
        )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_ask_question_endpoint_rejects_invalid_limit() -> None:
    app.dependency_overrides[get_current_membership] = lambda: object()

    try:
        client = TestClient(app)

        response = client.post(
            "/api/v1/ai/tenants/11111111-1111-1111-1111-111111111111/ask",
            json={
                "question": "Where is my shipment?",
                "limit": 0,
            },
        )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_ask_question_endpoint_rejects_invalid_tenant_id() -> None:
    app.dependency_overrides[get_current_membership] = lambda: object()

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
