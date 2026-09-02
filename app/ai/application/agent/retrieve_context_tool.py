from app.ai.application.agent.context import AgentContext
from app.ai.application.services.retrieve_context import RetrieveContextService
from app.ai.domain.rag_models import RetrievedChunk


class RetrieveContextTool:
    def __init__(
        self,
        *,
        retrieve_context_service: RetrieveContextService,
    ) -> None:
        self._retrieve_context_service = retrieve_context_service

    async def execute(
        self,
        *,
        context: AgentContext,
        query: str,
        limit: int = 5,
    ) -> tuple[RetrievedChunk, ...]:
        return await self._retrieve_context_service.execute(
            tenant_id=context.tenant_id,
            query=query,
            limit=limit,
        )
