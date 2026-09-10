from datetime import timedelta
from typing import cast
from uuid import UUID

from langgraph.graph import END, START, StateGraph

from app.ai.application.agent.context import AgentContext
from app.ai.application.agent.get_shipment_tool import GetShipmentTool
from app.ai.application.agent.retrieve_context_tool import RetrieveContextTool
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


class LangGraphAgentRuntime:
    def __init__(
        self,
        *,
        agent_planner: AgentPlanner,
        resolve_shipment_service: ResolveShipmentService,
        get_shipment_tool: GetShipmentTool,
        summarize_shipment_service: SummarizeShipmentService,
        analyze_shipment_service: AnalyzeShipmentService,
        retrieve_context_tool: RetrieveContextTool,
        generate_text_service: GenerateTextService,
    ) -> None:
        self._agent_planner = agent_planner
        self._resolve_shipment_service = resolve_shipment_service
        self._get_shipment_tool = get_shipment_tool
        self._summarize_shipment_service = summarize_shipment_service
        self._analyze_shipment_service = analyze_shipment_service
        self._retrieve_context_tool = retrieve_context_tool
        self._generate_text_service = generate_text_service

        graph = StateGraph(AgentState)

        graph.add_node(
            "plan",
            self._plan,
        )

        graph.add_node(
            "resolve_shipment",
            self._resolve_shipment,
        )

        graph.add_node(
            "get_shipment",
            self._get_shipment,
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
            "plan",
        )

        graph.add_conditional_edges(
            "plan",
            self._route_after_plan,
            {
                "direct_answer": "answer",
                "get_shipment": "resolve_shipment",
                "summarize_shipment": "resolve_shipment",
                "analyze_shipment_operations": "resolve_shipment",
                "retrieve_context": "retrieve_context",
            },
        )

        graph.add_conditional_edges(
            "resolve_shipment",
            self._route_after_shipment_resolution,
            {
                "get_shipment": "get_shipment",
                "summarize_shipment": "summarize_shipment",
                "analyze_shipment_operations": ("analyze_shipment_operations"),
            },
        )

        graph.add_edge(
            "get_shipment",
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
        question: str,
    ) -> str:
        result = cast(
            AgentState,
            await self._graph.ainvoke(
                AgentState(
                    tenant_id=tenant_id,
                    question=question,
                    route=None,
                    shipment_identifier=None,
                    shipment_id=None,
                    tool_result=None,
                    answer="",
                )
            ),
        )

        return result["answer"]

    async def _plan(
        self,
        state: AgentState,
    ) -> AgentState:
        decision = await self._agent_planner.plan(
            question=state["question"],
        )

        return {
            **state,
            "route": decision.route,
            "shipment_identifier": decision.shipment_identifier,
            "shipment_id": None,
        }

    def _route_after_plan(
        self,
        state: AgentState,
    ) -> str:
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

        resolved_shipment = await self._resolve_shipment_service.execute(
            tenant_id=state["tenant_id"],
            identifier=shipment_identifier,
        )

        return {
            **state,
            "shipment_id": resolved_shipment.shipment_id,
        }

    def _route_after_shipment_resolution(
        self,
        state: AgentState,
    ) -> str:
        route = state["route"]

        if route not in {
            "get_shipment",
            "summarize_shipment",
            "analyze_shipment_operations",
        }:
            raise RuntimeError("Resolved shipment cannot be routed to this agent action")

        return route

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
