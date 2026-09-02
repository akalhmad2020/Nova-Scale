# tests/unit/ai/fakes.py

from uuid import UUID

from app.ai.application.agent.decision import AgentDecision
from app.ai.domain.models import LLMRequest, LLMResponse
from app.ai.domain.rag_models import EmbeddedChunk, RetrievedChunk


class FakeLLMProvider:
    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []
        self.response = LLMResponse(
            content="fake response",
            model="fake-model",
        )

    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        self.requests.append(request)
        return self.response


class FakeEmbeddingProvider:
    def __init__(self) -> None:
        self.texts: list[tuple[str, ...]] = []

    async def embed_text(
        self,
        text: str,
    ) -> tuple[float, ...]:
        return (0.1, 0.2, 0.3)

    async def embed_texts(
        self,
        texts: tuple[str, ...],
    ) -> tuple[tuple[float, ...], ...]:
        self.texts.append(texts)

        return tuple((float(index), float(index + 1)) for index, _ in enumerate(texts))


class FakeVectorStore:
    def __init__(self) -> None:
        self.replaced_documents: list[
            tuple[
                UUID,
                str,
                tuple[EmbeddedChunk, ...],
            ]
        ] = []

        self.searches: list[
            tuple[
                UUID,
                tuple[float, ...],
                int,
            ]
        ] = []

        self.search_results: tuple[RetrievedChunk, ...] = ()

    async def replace_document(
        self,
        *,
        tenant_id: UUID,
        document_id: str,
        chunks: tuple[EmbeddedChunk, ...],
    ) -> None:
        self.replaced_documents.append(
            (
                tenant_id,
                document_id,
                chunks,
            )
        )

    async def search(
        self,
        *,
        tenant_id: UUID,
        query_embedding: tuple[float, ...],
        limit: int = 5,
    ) -> tuple[RetrievedChunk, ...]:
        self.searches.append(
            (
                tenant_id,
                query_embedding,
                limit,
            )
        )

        return self.search_results


class FakeAgentPlanner:
    def __init__(self) -> None:
        self.questions: list[str] = []
        self.decision = AgentDecision(
            route="direct_answer",
        )

    async def plan(
        self,
        *,
        question: str,
    ) -> AgentDecision:
        self.questions.append(question)
        return self.decision
