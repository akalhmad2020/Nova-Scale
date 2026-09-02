import json
from uuid import UUID

from app.ai.application.agent.decision import (
    AgentDecision,
    AgentRoute,
)
from app.ai.application.agent.exceptions import AgentPlanningError
from app.ai.application.services.generate_text import GenerateTextService


class LLMAgentPlanner:
    def __init__(
        self,
        *,
        generate_text_service: GenerateTextService,
    ) -> None:
        self._generate_text_service = generate_text_service

    async def plan(
        self,
        *,
        question: str,
    ) -> AgentDecision:
        response = await self._generate_text_service.execute(
            prompt=question,
            system_prompt=(
                "You are the NovaScale agent planner. "
                "Choose exactly one route for the user's request.\n\n"
                "Available routes:\n"
                '- "direct_answer": use when no shipment lookup or document '
                "retrieval is required.\n"
                '- "get_shipment": use when the user wants information about '
                "a specific shipment and provides its UUID.\n"
                '- "retrieve_context": use when the user asks a question that '
                "should be answered from NovaScale tenant documents or stored "
                "knowledge.\n\n"
                "Return JSON only using exactly this shape:\n"
                '{"route":"direct_answer","shipment_id":null}\n'
                "or\n"
                '{"route":"get_shipment","shipment_id":"<uuid>"}\n'
                "or\n"
                '{"route":"retrieve_context","shipment_id":null}\n\n'
                "Do not include markdown, explanations, or additional fields."
            ),
            temperature=0.0,
        )

        payload = self._parse_payload(response.content)

        route_value = payload.get("route")

        route: AgentRoute

        if route_value == "direct_answer":
            route = "direct_answer"
        elif route_value == "get_shipment":
            route = "get_shipment"
        elif route_value == "retrieve_context":
            route = "retrieve_context"
        else:
            raise AgentPlanningError("Agent planner returned an unsupported route")

        shipment_id_value = payload.get("shipment_id")

        if route in {
            "direct_answer",
            "retrieve_context",
        }:
            return AgentDecision(
                route=route,
                shipment_id=None,
            )

        if not isinstance(shipment_id_value, str):
            raise AgentPlanningError("Shipment id is required for get_shipment route")

        try:
            shipment_id = UUID(shipment_id_value)
        except ValueError as exc:
            raise AgentPlanningError("Agent planner returned an invalid shipment id") from exc

        return AgentDecision(
            route=route,
            shipment_id=shipment_id,
        )

    @staticmethod
    def _parse_payload(
        content: str,
    ) -> dict[str, object]:
        stripped = content.strip()

        start = stripped.find("{")
        end = stripped.rfind("}")

        if start == -1 or end == -1 or end < start:
            raise AgentPlanningError("Agent planner did not return a JSON object")

        json_content = stripped[start : end + 1]

        try:
            payload = json.loads(json_content)
        except json.JSONDecodeError as exc:
            raise AgentPlanningError("Agent planner returned invalid JSON") from exc

        if not isinstance(payload, dict):
            raise AgentPlanningError("Agent planner JSON must be an object")

        return {str(key): value for key, value in payload.items()}
