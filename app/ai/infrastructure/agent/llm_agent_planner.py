import json

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
                "Classify the user's request into exactly one route.\n\n"
                "Routes:\n"
                '- "direct_answer": general questions that do not require '
                "shipment data, operational analysis, or tenant documents.\n"
                '- "get_shipment": factual lookup of a specific shipment. '
                "Use this for requests about its current status, tracking "
                "number, reference, service type, weight, description, or "
                "other direct shipment facts.\n"
                '- "summarize_shipment": requests to summarize, review, '
                "explain, or provide an overview of a specific shipment "
                "including its timeline.\n"
                '- "analyze_shipment_operations": requests to detect or '
                "explain operational problems, risks, anomalies, stale "
                "activity, stalled movement, inconsistent timeline events, "
                "or anything that requires operational attention.\n"
                '- "retrieve_context": questions that should be answered '
                "from NovaScale tenant documents or stored knowledge.\n\n"
                "Important routing rules:\n"
                "- Asking only for a shipment current status is "
                '"get_shipment", NOT "analyze_shipment_operations".\n'
                "- Asking where a shipment is or what its current state is "
                'uses "get_shipment".\n'
                '- Use "analyze_shipment_operations" only when the user asks '
                "about problems, risks, delays, anomalies, warnings, stale "
                "activity, or operational concerns.\n"
                '- Use "summarize_shipment" when the user explicitly asks '
                "for a summary, overview, review, explanation, or timeline.\n\n"
                "A shipment may be identified by UUID, tracking number, "
                "or reference. For shipment routes, copy the identifier "
                "exactly as provided by the user. Never convert or invent it.\n\n"
                "Examples:\n"
                '"What is the status of SHIP-001?" -> get_shipment\n'
                '"Where is SHIP-001?" -> get_shipment\n'
                '"Summarize SHIP-001" -> summarize_shipment\n'
                '"Is anything wrong with SHIP-001?" '
                "-> analyze_shipment_operations\n"
                '"Has SHIP-001 stalled?" '
                "-> analyze_shipment_operations\n\n"
                "Return JSON only. No markdown and no explanation.\n\n"
                "Valid shapes:\n"
                '{"route":"direct_answer","shipment_identifier":null}\n'
                '{"route":"get_shipment",'
                '"shipment_identifier":"<identifier>"}\n'
                '{"route":"summarize_shipment",'
                '"shipment_identifier":"<identifier>"}\n'
                '{"route":"analyze_shipment_operations",'
                '"shipment_identifier":"<identifier>"}\n'
                '{"route":"retrieve_context","shipment_identifier":null}'
            ),
            temperature=0.0,
            max_tokens=128,
        )

        payload = self._parse_payload(
            response.content,
        )

        route_value = payload.get("route")

        route: AgentRoute

        if route_value == "direct_answer":
            route = "direct_answer"
        elif route_value == "get_shipment":
            route = "get_shipment"
        elif route_value == "summarize_shipment":
            route = "summarize_shipment"
        elif route_value == "analyze_shipment_operations":
            route = "analyze_shipment_operations"
        elif route_value == "retrieve_context":
            route = "retrieve_context"
        else:
            raise AgentPlanningError("Agent planner returned an unsupported route")

        if route in {
            "direct_answer",
            "retrieve_context",
        }:
            return AgentDecision(
                route=route,
                shipment_identifier=None,
            )

        shipment_identifier_value = payload.get("shipment_identifier")

        if not isinstance(
            shipment_identifier_value,
            str,
        ):
            raise AgentPlanningError("Shipment identifier is required for shipment route")

        shipment_identifier = shipment_identifier_value.strip()

        if not shipment_identifier:
            raise AgentPlanningError("Shipment identifier is required for shipment route")

        return AgentDecision(
            route=route,
            shipment_identifier=shipment_identifier,
        )

    @classmethod
    def _parse_payload(
        cls,
        content: str,
    ) -> dict[str, object]:
        stripped = content.strip()

        start = stripped.find("{")
        end = stripped.rfind("}")

        if start == -1 or end == -1 or end < start:
            raise AgentPlanningError("Agent planner did not return a JSON object")

        json_content = stripped[start : end + 1]

        payload = cls._decode_json(
            json_content,
        )

        if not isinstance(payload, dict):
            raise AgentPlanningError("Agent planner JSON must be an object")

        return {str(key): value for key, value in payload.items()}

    @staticmethod
    def _decode_json(
        content: str,
    ) -> object:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        repaired_content = content.replace(
            r"\:null",
            '":null',
        ).replace(
            r'\:"',
            '":"',
        )

        if repaired_content == content:
            raise AgentPlanningError("Agent planner returned invalid JSON")

        try:
            return json.loads(repaired_content)
        except json.JSONDecodeError as exc:
            raise AgentPlanningError("Agent planner returned invalid JSON") from exc
