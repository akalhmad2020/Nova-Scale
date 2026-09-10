import logging
from datetime import timedelta
from typing import cast
from uuid import UUID

from langgraph.graph import END, START, StateGraph

from app.ai.application.agent.authorization import (
    AgentAuthorizationContext,
    AgentAuthorizationService,
)
from app.ai.application.agent.context import AgentContext
from app.ai.application.agent.conversation import (
    AgentContinuation,
    AgentExecutionResult,
)
from app.ai.application.agent.conversation_context import (
    ConversationContext,
)
from app.ai.application.agent.exceptions import AgentPlanningError
from app.ai.application.agent.get_shipment_tool import GetShipmentTool
from app.ai.application.agent.retrieve_context_tool import RetrieveContextTool
from app.ai.application.agent.shipment_resolution_exceptions import (
    ShipmentIdentifierAmbiguousError,
)
from app.ai.application.agent.shipment_resolution_models import (
    MultiShipmentResolutionItem,
)
from app.ai.application.agent.state import AgentState
from app.ai.application.ports.agent_planner import AgentPlanner
from app.ai.application.services.analyze_shipment import (
    AnalyzeShipmentService,
)
from app.ai.application.services.generate_text import GenerateTextService
from app.ai.application.services.resolve_shipment import ResolveShipmentService
from app.ai.application.services.summarize_shipment import (
    SummarizeShipmentService,
)
from app.modules.shipments.application.exceptions import ShipmentNotFoundError

logger = logging.getLogger("novascale.ai")


class LangGraphAgentRuntime:
    def __init__(
        self,
        *,
        agent_planner: AgentPlanner,
        authorization_service: AgentAuthorizationService,
        resolve_shipment_service: ResolveShipmentService,
        get_shipment_tool: GetShipmentTool,
        summarize_shipment_service: SummarizeShipmentService,
        analyze_shipment_service: AnalyzeShipmentService,
        retrieve_context_tool: RetrieveContextTool,
        generate_text_service: GenerateTextService,
    ) -> None:
        self._agent_planner = agent_planner
        self._authorization_service = authorization_service
        self._resolve_shipment_service = resolve_shipment_service
        self._get_shipment_tool = get_shipment_tool
        self._summarize_shipment_service = summarize_shipment_service
        self._analyze_shipment_service = analyze_shipment_service
        self._retrieve_context_tool = retrieve_context_tool
        self._generate_text_service = generate_text_service

        graph = StateGraph(AgentState)

        graph.add_node(
            "prepare",
            self._prepare,
        )

        graph.add_node(
            "plan",
            self._plan,
        )

        graph.add_node(
            "authorize",
            self._authorize,
        )

        graph.add_node(
            "resolve_shipment",
            self._resolve_shipment,
        )

        graph.add_node(
            "resolve_shipments",
            self._resolve_shipments,
        )

        graph.add_node(
            "get_shipment",
            self._get_shipment,
        )

        graph.add_node(
            "get_shipments",
            self._get_shipments,
        )

        graph.add_node(
            "summarize_shipment",
            self._summarize_shipment,
        )

        graph.add_node(
            "analyze_shipment_operations",
            self._analyze_shipment_operations,
        )

        graph.add_node(
            "retrieve_context",
            self._retrieve_context,
        )

        graph.add_node(
            "answer",
            self._answer,
        )

        graph.add_edge(
            START,
            "prepare",
        )

        graph.add_conditional_edges(
            "prepare",
            self._route_after_prepare,
            {
                "plan": "plan",
                "authorize": "authorize",
            },
        )

        graph.add_edge(
            "plan",
            "authorize",
        )

        graph.add_conditional_edges(
            "authorize",
            self._route_after_authorization,
            {
                "denied": END,
                "direct_answer": "answer",
                "get_shipment": "resolve_shipment",
                "summarize_shipment": "resolve_shipment",
                "analyze_shipment_operations": "resolve_shipment",
                "retrieve_context": "retrieve_context",
                "get_shipments": "resolve_shipments",
            },
        )

        graph.add_conditional_edges(
            "resolve_shipment",
            self._route_after_shipment_resolution,
            {
                "ambiguous": END,
                "get_shipment": "get_shipment",
                "summarize_shipment": "summarize_shipment",
                "analyze_shipment_operations": "analyze_shipment_operations",
            },
        )

        graph.add_conditional_edges(
            "resolve_shipments",
            self._route_after_multi_shipment_resolution,
            {
                "ambiguous": END,
                "get_shipments": "get_shipments",
            },
        )

        graph.add_edge(
            "get_shipment",
            "answer",
        )

        graph.add_edge(
            "get_shipments",
            "answer",
        )

        graph.add_edge(
            "summarize_shipment",
            END,
        )

        graph.add_edge(
            "analyze_shipment_operations",
            "answer",
        )

        graph.add_edge(
            "retrieve_context",
            "answer",
        )

        graph.add_edge(
            "answer",
            END,
        )

        self._graph = graph.compile()

    async def execute(
        self,
        *,
        tenant_id: UUID,
        role_id: UUID,
        question: str,
        conversation_context: ConversationContext | None = None,
    ) -> str:
        result = await self.execute_with_context(
            tenant_id=tenant_id,
            role_id=role_id,
            question=question,
            continuation=None,
            conversation_context=conversation_context,
        )

        return result.answer

    async def execute_with_context(
        self,
        *,
        tenant_id: UUID,
        role_id: UUID,
        question: str,
        continuation: AgentContinuation | None = None,
        conversation_context: ConversationContext | None = None,
    ) -> AgentExecutionResult:
        continuation_route = continuation.route if continuation is not None else None

        continuation_original_identifier = (
            continuation.original_identifier if continuation is not None else None
        )

        result = cast(
            AgentState,
            await self._graph.ainvoke(
                AgentState(
                    tenant_id=tenant_id,
                    role_id=role_id,
                    question=question,
                    route=None,
                    conversation_context=conversation_context,
                    shipment_identifier=None,
                    shipment_id=None,
                    continuation_route=continuation_route,
                    continuation_original_identifier=(continuation_original_identifier),
                    shipment_resolution_ambiguous=False,
                    tool_result=None,
                    authorization_denied=False,
                    answer="",
                    shipment_identifiers=(),
                    shipment_ids=(),
                    shipment_resolutions=(),
                )
            ),
        )

        result_continuation: AgentContinuation | None = None

        if result["shipment_resolution_ambiguous"]:
            route = result["route"]

            if route == "get_shipments":
                return AgentExecutionResult(
                    answer=result["answer"],
                    continuation=None,
                )

            original_identifier = result["continuation_original_identifier"]

            if route not in {
                "get_shipment",
                "summarize_shipment",
                "analyze_shipment_operations",
            }:
                raise RuntimeError(
                    "Ambiguous shipment resolution requires a shipment continuation route"
                )

            if original_identifier is None:
                raise RuntimeError("Ambiguous shipment resolution requires an original identifier")

            result_continuation = AgentContinuation(
                kind="shipment_selection",
                route=route,
                original_identifier=original_identifier,
            )

        return AgentExecutionResult(
            answer=result["answer"],
            continuation=result_continuation,
        )

    async def _prepare(
        self,
        state: AgentState,
    ) -> AgentState:
        continuation_route = state["continuation_route"]

        if continuation_route is None:
            return {
                **state,
                "route": None,
                "shipment_identifier": None,
                "shipment_id": None,
                "shipment_identifiers": (),
                "shipment_ids": (),
                "shipment_resolutions": (),
                "shipment_resolution_ambiguous": False,
            }

        shipment_identifier = state["question"].strip()

        if not shipment_identifier:
            raise RuntimeError("Shipment identifier is required for shipment continuation")

        return {
            **state,
            "route": continuation_route,
            "shipment_identifier": shipment_identifier,
            "shipment_id": None,
            "shipment_identifiers": (),
            "shipment_ids": (),
            "shipment_resolutions": (),
            "shipment_resolution_ambiguous": False,
        }

    @staticmethod
    def _route_after_prepare(
        state: AgentState,
    ) -> str:
        if state["continuation_route"] is not None:
            return "authorize"

        return "plan"

    async def _plan(
        self,
        state: AgentState,
    ) -> AgentState:
        decision = None

        for attempt in range(1, 3):
            try:
                decision = await self._agent_planner.plan(
                    question=state["question"],
                    conversation_context=state["conversation_context"],
                )
                break
            except AgentPlanningError:
                if attempt == 1:
                    logger.warning(
                        "AI agent planner attempt failed",
                        extra={
                            "ai_operation": "agent_planning",
                            "ai_outcome": "retry",
                            "attempt": attempt,
                        },
                    )

        if decision is None:
            logger.warning(
                "AI agent planner fallback activated",
                extra={
                    "ai_operation": "agent_planning",
                    "ai_outcome": "fallback",
                    "attempts": 2,
                },
            )

            return {
                **state,
                "route": "direct_answer",
                "shipment_identifier": None,
                "shipment_id": None,
                "shipment_identifiers": (),
                "shipment_ids": (),
                "shipment_resolutions": (),
                "continuation_route": None,
                "continuation_original_identifier": None,
                "shipment_resolution_ambiguous": False,
            }

        return {
            **state,
            "route": decision.route,
            "shipment_identifier": decision.shipment_identifier,
            "shipment_id": None,
            "shipment_identifiers": decision.shipment_identifiers,
            "shipment_ids": (),
            "shipment_resolutions": (),
            "continuation_route": None,
            "continuation_original_identifier": None,
            "shipment_resolution_ambiguous": False,
        }

    async def _authorize(
        self,
        state: AgentState,
    ) -> AgentState:
        route = state["route"]

        if route is None:
            raise RuntimeError("Agent route was not selected")

        allowed = await self._authorization_service.is_allowed(
            context=AgentAuthorizationContext(
                role_id=state["role_id"],
            ),
            route=route,
        )

        if allowed:
            return {
                **state,
                "authorization_denied": False,
            }

        return {
            **state,
            "authorization_denied": True,
            "answer": ("You do not have permission to use the requested NovaScale capability."),
        }

    def _route_after_authorization(
        self,
        state: AgentState,
    ) -> str:
        if state["authorization_denied"]:
            return "denied"

        route = state["route"]

        if route is None:
            raise RuntimeError("Agent route was not selected")

        return route

    async def _resolve_shipment(
        self,
        state: AgentState,
    ) -> AgentState:
        shipment_identifier = state["shipment_identifier"]

        if shipment_identifier is None:
            raise RuntimeError("Shipment identifier is required for shipment route")

        try:
            resolved_shipment = await self._resolve_shipment_service.execute(
                tenant_id=state["tenant_id"],
                identifier=shipment_identifier,
            )
        except ShipmentIdentifierAmbiguousError:
            return {
                **state,
                "shipment_id": None,
                "continuation_route": state["route"],
                "continuation_original_identifier": shipment_identifier,
                "shipment_resolution_ambiguous": True,
                "answer": (
                    f"I found multiple shipments matching "
                    f"'{shipment_identifier}'. "
                    "Please provide the shipment tracking number or UUID "
                    "so I can identify the correct shipment."
                ),
            }

        return {
            **state,
            "shipment_id": resolved_shipment.shipment_id,
            "shipment_resolution_ambiguous": False,
        }

    async def _resolve_shipments(
        self,
        state: AgentState,
    ) -> AgentState:
        shipment_identifiers = state["shipment_identifiers"]

        if len(shipment_identifiers) < 2:
            raise RuntimeError(
                "At least two shipment identifiers are required for get_shipments route"
            )

        shipment_ids: list[UUID] = []
        resolutions: list[MultiShipmentResolutionItem] = []

        for shipment_identifier in shipment_identifiers:
            try:
                resolved_shipment = await self._resolve_shipment_service.execute(
                    tenant_id=state["tenant_id"],
                    identifier=shipment_identifier,
                )
            except ShipmentIdentifierAmbiguousError:
                resolutions.append(
                    MultiShipmentResolutionItem(
                        identifier=shipment_identifier,
                        status="ambiguous",
                    )
                )
                continue
            except ShipmentNotFoundError:
                resolutions.append(
                    MultiShipmentResolutionItem(
                        identifier=shipment_identifier,
                        status="not_found",
                    )
                )
                continue

            shipment_ids.append(
                resolved_shipment.shipment_id,
            )

            resolutions.append(
                MultiShipmentResolutionItem(
                    identifier=shipment_identifier,
                    status="resolved",
                    shipment_id=resolved_shipment.shipment_id,
                    identifier_kind=resolved_shipment.identifier_kind,
                )
            )

        return {
            **state,
            "shipment_ids": tuple(shipment_ids),
            "shipment_resolutions": tuple(resolutions),
            "shipment_resolution_ambiguous": False,
        }

    def _route_after_shipment_resolution(
        self,
        state: AgentState,
    ) -> str:
        if state["shipment_resolution_ambiguous"]:
            return "ambiguous"

        route = state["route"]

        if route not in {
            "get_shipment",
            "summarize_shipment",
            "analyze_shipment_operations",
        }:
            raise RuntimeError("Resolved shipment cannot be routed to this agent action")

        return route

    @staticmethod
    def _route_after_multi_shipment_resolution(
        state: AgentState,
    ) -> str:
        if not state["shipment_resolutions"]:
            raise RuntimeError(
                "Multi-shipment resolution results are required for get_shipments route"
            )

        return "get_shipments"

    async def _get_shipment(
        self,
        state: AgentState,
    ) -> AgentState:
        shipment_id = state["shipment_id"]

        if shipment_id is None:
            raise RuntimeError("Shipment id is required for get_shipment route")

        result = await self._get_shipment_tool.execute(
            context=AgentContext(
                tenant_id=state["tenant_id"],
            ),
            shipment_id=shipment_id,
        )

        return {
            **state,
            "tool_result": (
                f"Shipment id: {result.id}\n"
                f"Tracking number: {result.tracking_number}\n"
                f"Reference: {result.reference}\n"
                f"Status: {result.status}\n"
                f"Service type: {result.service_type}\n"
                f"Description: {result.description}\n"
                f"Weight: {result.weight} {result.weight_unit}\n"
                f"Notes: {result.notes}"
            ),
        }

    async def _get_shipments(
        self,
        state: AgentState,
    ) -> AgentState:
        resolutions = state["shipment_resolutions"]

        if len(resolutions) < 2:
            raise RuntimeError(
                "At least two shipment resolution results are required for get_shipments route"
            )

        shipment_results: list[str] = []

        for index, resolution in enumerate(
            resolutions,
            start=1,
        ):
            if resolution.status == "not_found":
                shipment_results.append(
                    f"Shipment {index}:\n"
                    f"Identifier: {resolution.identifier}\n"
                    "Resolution status: not_found\n"
                    "The shipment could not be found "
                    "for the current tenant."
                )
                continue

            if resolution.status == "ambiguous":
                shipment_results.append(
                    f"Shipment {index}:\n"
                    f"Identifier: {resolution.identifier}\n"
                    "Resolution status: ambiguous\n"
                    "The identifier matches multiple shipments. "
                    "A tracking number or shipment UUID is required "
                    "to identify the shipment."
                )
                continue

            shipment_id = resolution.shipment_id

            if shipment_id is None:
                raise RuntimeError("Resolved multi-shipment item is missing its shipment id")

            result = await self._get_shipment_tool.execute(
                context=AgentContext(
                    tenant_id=state["tenant_id"],
                ),
                shipment_id=shipment_id,
            )

            shipment_results.append(
                f"Shipment {index}:\n"
                f"Identifier: {resolution.identifier}\n"
                "Resolution status: resolved\n"
                f"Shipment id: {result.id}\n"
                f"Tracking number: {result.tracking_number}\n"
                f"Reference: {result.reference}\n"
                f"Status: {result.status}\n"
                f"Service type: {result.service_type}\n"
                f"Description: {result.description}\n"
                f"Weight: {result.weight} {result.weight_unit}\n"
                f"Notes: {result.notes}"
            )

        return {
            **state,
            "tool_result": "\n\n".join(
                shipment_results,
            ),
        }

    async def _summarize_shipment(
        self,
        state: AgentState,
    ) -> AgentState:
        shipment_id = state["shipment_id"]

        if shipment_id is None:
            raise RuntimeError("Shipment id is required for summarize_shipment route")

        response = await self._summarize_shipment_service.execute(
            tenant_id=state["tenant_id"],
            shipment_id=shipment_id,
        )

        return {
            **state,
            "answer": response.content,
        }

    async def _analyze_shipment_operations(
        self,
        state: AgentState,
    ) -> AgentState:
        shipment_id = state["shipment_id"]

        if shipment_id is None:
            raise RuntimeError("Shipment id is required for analyze_shipment_operations route")

        analysis = await self._analyze_shipment_service.execute(
            tenant_id=state["tenant_id"],
            shipment_id=shipment_id,
        )

        if not analysis.issues:
            tool_result = (
                "No operational issues were detected for this shipment. "
                f"Highest severity: {analysis.highest_severity}. "
                f"Risk score: {analysis.risk_score}/100. "
                f"Risk level: {analysis.risk_level}."
            )
        else:
            issues = "\n".join(
                (
                    f"- code={issue.code}, "
                    f"severity={issue.severity}, "
                    f"age={self._format_issue_age(issue.age)}, "
                    f"message={issue.message}, "
                    f"recommended_action={issue.recommended_action}"
                )
                for issue in analysis.issues
            )

            tool_result = (
                "Shipment operational analysis:\n"
                f"Highest severity: {analysis.highest_severity}\n"
                f"Risk score: {analysis.risk_score}/100\n"
                f"Risk level: {analysis.risk_level}\n"
                f"Issue count: {len(analysis.issues)}\n"
                f"Issues:\n{issues}"
            )

        return {
            **state,
            "tool_result": tool_result,
        }

    async def _retrieve_context(
        self,
        state: AgentState,
    ) -> AgentState:
        retrieved_chunks = await self._retrieve_context_tool.execute(
            context=AgentContext(
                tenant_id=state["tenant_id"],
            ),
            query=state["question"],
        )

        if not retrieved_chunks:
            tool_result = "No relevant tenant document context was found for this question."
        else:
            tool_result = "\n\n".join(
                (
                    f"Document: {retrieved_chunk.chunk.document_id}\n"
                    f"Chunk: {retrieved_chunk.chunk.chunk_index}\n"
                    "Content:\n"
                    f"{retrieved_chunk.chunk.content}"
                )
                for retrieved_chunk in retrieved_chunks
            )

        return {
            **state,
            "tool_result": tool_result,
        }

    async def _answer(
        self,
        state: AgentState,
    ) -> AgentState:
        tool_result = state["tool_result"]

        if tool_result is None:
            prompt = state["question"]
        else:
            prompt = f"User question:\n{state['question']}\n\nTool result:\n{tool_result}"

        response = await self._generate_text_service.execute(
            prompt=prompt,
            system_prompt=(
                "You are the NovaScale AI agent. "
                "Answer clearly and concisely. "
                "When a tool result is provided, use only that result "
                "for factual information retrieved by the agent."
            ),
            temperature=0.0,
        )

        return {
            **state,
            "answer": response.content,
        }

    @staticmethod
    def _format_issue_age(
        age: timedelta | None,
    ) -> str:
        if age is None:
            return "not_applicable"

        total_seconds = max(
            0,
            int(age.total_seconds()),
        )

        hours, remainder = divmod(
            total_seconds,
            3600,
        )

        minutes = remainder // 60

        return f"{hours}h {minutes}m"
