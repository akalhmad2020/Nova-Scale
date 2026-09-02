from uuid import UUID

from app.ai.application.services.generate_text import GenerateTextService
from app.ai.application.services.retrieve_context import RetrieveContextService
from app.ai.domain.rag_models import RAGAnswer, RetrievedChunk


class AnswerQuestionService:
    def __init__(
        self,
        *,
        retrieve_context_service: RetrieveContextService,
        generate_text_service: GenerateTextService,
    ) -> None:
        self._retrieve_context_service = retrieve_context_service
        self._generate_text_service = generate_text_service

    async def execute(
        self,
        *,
        tenant_id: UUID,
        question: str,
        limit: int = 5,
    ) -> RAGAnswer:
        retrieved_chunks = await self._retrieve_context_service.execute(
            tenant_id=tenant_id,
            query=question,
            limit=limit,
        )

        if not retrieved_chunks:
            return RAGAnswer(
                content=("I do not have enough relevant information to answer this question."),
                model="none",
                sources=(),
            )

        context = self._build_context(retrieved_chunks)

        response = await self._generate_text_service.execute(
            prompt=self._build_prompt(
                question=question,
                context=context,
            ),
            system_prompt=(
                "You are the NovaScale AI assistant. "
                "Answer the user's question using only the provided context. "
                "Do not invent information that is not supported by the context. "
                "If the context is insufficient, say that you do not have enough "
                "information to answer."
            ),
            temperature=0.0,
        )

        return RAGAnswer(
            content=response.content,
            model=response.model,
            sources=retrieved_chunks,
        )

    @staticmethod
    def _build_context(
        retrieved_chunks: tuple[RetrievedChunk, ...],
    ) -> str:
        return "\n\n".join(
            (
                f"[Source {index}]\n"
                f"Document: {retrieved_chunk.chunk.document_id}\n"
                f"Content: {retrieved_chunk.chunk.content}"
            )
            for index, retrieved_chunk in enumerate(retrieved_chunks, start=1)
        )

    @staticmethod
    def _build_prompt(*, question: str, context: str) -> str:
        return (
            "Use the following context to answer the question.\n\n"
            f"Context:\n{context}\n\n"
            f"Question:\n{question}"
        )
