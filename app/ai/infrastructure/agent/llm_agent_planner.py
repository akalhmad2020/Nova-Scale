import json

from app.ai.application.agent.conversation_context import (
    ConversationContext,
)
from app.ai.application.agent.decision import (
    AgentDecision,
    AgentRoute,
)
from app.ai.application.agent.exceptions import AgentPlanningError
from app.ai.application.services.generate_text import GenerateTextService

MIN_MULTI_SHIPMENT_COUNT = 2
MAX_MULTI_SHIPMENT_COUNT = 5


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
        conversation_context: ConversationContext | None = None,
    ) -> AgentDecision:
        planner_prompt = self._build_planner_prompt(
            question=question,
            conversation_context=conversation_context,
        )
        response = await self._generate_text_service.execute(
            prompt=planner_prompt,
            system_prompt=(
                "You are the NovaScale agent planner. "
                "Classify the user's request into exactly one route.\n\n"
                "Routes:\n"
                '- "direct_answer": general questions that do not require '
                "shipment data, operational analysis, or tenant documents.\n"
                '- "get_shipment": factual lookup of exactly one shipment. '
                "Use this for current status, tracking number, reference, "
                "service type, weight, description, or other direct facts.\n"
                '- "get_shipments": factual lookup, status review, or '
                "comparison involving two to five specific shipments.\n"
                '- "summarize_shipment": requests to summarize, review, '
                "explain, or provide an overview of one specific shipment "
                "including its timeline.\n"
                '- "analyze_shipment_operations": requests to detect or '
                "explain operational problems, risks, anomalies, stale "
                "activity, stalled movement, inconsistent timeline events, "
                "or anything that requires operational attention for one "
                "specific shipment.\n"
                '- "retrieve_context": questions that should be answered '
                "from NovaScale tenant documents or stored knowledge.\n\n"
                "Important routing rules:\n"
                "- Asking only for one shipment's current status is "
                '"get_shipment", NOT "analyze_shipment_operations".\n'
                "- Asking for facts or status about multiple shipments uses "
                '"get_shipments".\n'
                "- Comparing two or more shipments uses "
                '"get_shipments".\n'
                '- Use "analyze_shipment_operations" only when the user asks '
                "about problems, risks, delays, anomalies, warnings, stale "
                "activity, or operational concerns.\n"
                '- Use "summarize_shipment" when the user explicitly asks '
                "for a summary, overview, review, explanation, or timeline "
                "of one shipment.\n\n"
                "A shipment may be identified by UUID, tracking number, "
                "or reference. Copy identifiers exactly as provided by the "
                "user. Never convert or invent them.\n\n"
                "For get_shipments, return between two and five identifiers "
                "in shipment_identifiers, preserving their user-provided "
                "order.\n\n"
                "Examples:\n"
                '"What is the status of SHIP-001?" -> get_shipment\n'
                '"Compare SHIP-001 and SHIP-002" -> get_shipments\n'
                '"What are the statuses of A-100, A-101 and A-102?" '
                "-> get_shipments\n"
                '"Summarize SHIP-001" -> summarize_shipment\n'
                '"Is anything wrong with SHIP-001?" '
                "-> analyze_shipment_operations\n"
                '"Has SHIP-001 stalled?" '
                "-> analyze_shipment_operations\n\n"
                "Return JSON only. No markdown and no explanation.\n\n"
                "Valid shapes:\n"
                '{"route":"direct_answer",'
                '"shipment_identifier":null,'
                '"shipment_identifiers":[]}\n'
                '{"route":"get_shipment",'
                '"shipment_identifier":"<identifier>",'
                '"shipment_identifiers":[]}\n'
                '{"route":"get_shipments",'
                '"shipment_identifier":null,'
                '"shipment_identifiers":["<identifier1>","<identifier2>"]}\n'
                '{"route":"summarize_shipment",'
                '"shipment_identifier":"<identifier>",'
                '"shipment_identifiers":[]}\n'
                '{"route":"analyze_shipment_operations",'
                '"shipment_identifier":"<identifier>",'
                '"shipment_identifiers":[]}\n'
                '{"route":"retrieve_context",'
                '"shipment_identifier":null,'
                '"shipment_identifiers":[]}'
            ),
            temperature=0.0,
            max_tokens=192,
        )

        payload = self._parse_payload(
            response.content,
        )

        route = self._parse_route(
            payload.get("route"),
        )

        if route in {
            "direct_answer",
            "retrieve_context",
        }:
            return AgentDecision(
                route=route,
            )

        if route == "get_shipments":
            shipment_identifiers = self._parse_shipment_identifiers(
                payload.get("shipment_identifiers"),
            )

            return AgentDecision(
                route=route,
                shipment_identifiers=shipment_identifiers,
            )

        shipment_identifier = self._parse_shipment_identifier(
            payload.get("shipment_identifier"),
        )

        return AgentDecision(
            route=route,
            shipment_identifier=shipment_identifier,
        )

    @staticmethod
    def _build_planner_prompt(
        *,
        question: str,
        conversation_context: ConversationContext | None,
    ) -> str:
        if conversation_context is None or conversation_context.is_empty:
            return question

        history = "\n".join(
            f"{message.role}: {message.content}" for message in conversation_context.messages
        )

        return f"Conversation history:\n{history}\n\nCurrent user message:\n{question}"

    @staticmethod
    def _parse_route(
        route_value: object,
    ) -> AgentRoute:
        if route_value == "direct_answer":
            return "direct_answer"

        if route_value == "get_shipment":
            return "get_shipment"

        if route_value == "get_shipments":
            return "get_shipments"

        if route_value == "summarize_shipment":
            return "summarize_shipment"

        if route_value == "analyze_shipment_operations":
            return "analyze_shipment_operations"

        if route_value == "retrieve_context":
            return "retrieve_context"

        raise AgentPlanningError("Agent planner returned an unsupported route")

    @staticmethod
    def _parse_shipment_identifier(
        value: object,
    ) -> str:
        if not isinstance(
            value,
            str,
        ):
            raise AgentPlanningError("Shipment identifier is required for shipment route")

        shipment_identifier = value.strip()

        if not shipment_identifier:
            raise AgentPlanningError("Shipment identifier is required for shipment route")

        return shipment_identifier

    @staticmethod
    def _parse_shipment_identifiers(
        value: object,
    ) -> tuple[str, ...]:
        if not isinstance(
            value,
            list,
        ):
            raise AgentPlanningError("Shipment identifiers are required for multi-shipment route")

        identifiers: list[str] = []

        for item in value:
            if not isinstance(
                item,
                str,
            ):
                raise AgentPlanningError("Shipment identifiers must be strings")

            identifier = item.strip()

            if not identifier:
                raise AgentPlanningError("Shipment identifiers must not be empty")

            identifiers.append(
                identifier,
            )

        if not (MIN_MULTI_SHIPMENT_COUNT <= len(identifiers) <= MAX_MULTI_SHIPMENT_COUNT):
            raise AgentPlanningError(
                "Multi-shipment requests require between "
                f"{MIN_MULTI_SHIPMENT_COUNT} and "
                f"{MAX_MULTI_SHIPMENT_COUNT} shipment identifiers"
            )

        if len(set(identifiers)) != len(identifiers):
            raise AgentPlanningError("Multi-shipment identifiers must be unique")

        return tuple(
            identifiers,
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

        if not isinstance(
            payload,
            dict,
        ):
            raise AgentPlanningError("Agent planner JSON must be an object")

        return {str(key): value for key, value in payload.items()}

    @staticmethod
    def _decode_json(
        content: str,
    ) -> object:
        try:
            return json.loads(
                content,
            )
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
            return json.loads(
                repaired_content,
            )
        except json.JSONDecodeError as exc:
            raise AgentPlanningError("Agent planner returned invalid JSON") from exc
