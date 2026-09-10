import json

from app.ai.application.agent.conversation_context import ConversationContext
from app.ai.application.agent.decision import AgentDecision, AgentRoute
from app.ai.application.agent.exceptions import AgentPlanningError
from app.ai.application.services.generate_text import GenerateTextService
from app.modules.shipments.domain.enums import ShipmentStatus

MIN_MULTI_SHIPMENT_COUNT = 2
MAX_MULTI_SHIPMENT_COUNT = 5
MAX_AI_NOTES_LENGTH = 2000


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
            system_prompt=self._build_system_prompt(),
            temperature=0.0,
            max_tokens=256,
        )

        payload = self._parse_payload(response.content)
        route = self._parse_route(payload.get("route"))

        if route in {
            "direct_answer",
            "retrieve_context",
        }:
            return AgentDecision(route=route)

        if route == "get_shipments":
            shipment_identifiers = self._parse_shipment_identifiers(
                payload.get("shipment_identifiers")
            )

            return AgentDecision(
                route=route,
                shipment_identifiers=shipment_identifiers,
            )

        shipment_identifier = self._parse_shipment_identifier(payload.get("shipment_identifier"))

        if route == "transition_shipment_status":
            target_status = self._parse_target_status(payload.get("target_status"))

            return AgentDecision(
                route=route,
                shipment_identifier=shipment_identifier,
                target_shipment_status=target_status,
            )

        if route == "update_shipment_notes":
            shipment_notes = self._parse_shipment_notes(payload.get("shipment_notes"))

            return AgentDecision(
                route=route,
                shipment_identifier=shipment_identifier,
                shipment_notes=shipment_notes,
            )

        return AgentDecision(
            route=route,
            shipment_identifier=shipment_identifier,
        )

    @staticmethod
    def _build_system_prompt() -> str:
        statuses = ", ".join(status.value for status in ShipmentStatus)

        return (
            "You are the NovaScale agent planner. "
            "Classify the user's request into exactly one route.\n\n"
            "Routes:\n"
            '- "direct_answer": general questions that do not require '
            "shipment data, operational analysis, tenant documents, or a "
            "NovaScale write action.\n"
            '- "get_shipment": factual lookup of exactly one shipment. '
            "Use this for current status, tracking number, reference, "
            "service type, weight, description, notes, or other direct facts.\n"
            '- "get_shipments": factual lookup, status review, or comparison '
            "involving two to five specific shipments.\n"
            '- "summarize_shipment": summarize, review, explain, or provide '
            "an overview of one shipment including its timeline.\n"
            '- "analyze_shipment_operations": detect or explain operational '
            "problems, risks, anomalies, stale activity, stalled movement, "
            "or timeline inconsistencies for one shipment.\n"
            '- "retrieve_context": answer from NovaScale tenant documents or '
            "stored knowledge.\n"
            '- "transition_shipment_status": the user explicitly asks to '
            "change, move, mark, or transition one shipment to another "
            "shipment status. This is a write action and requires confirmation.\n"
            '- "update_shipment_notes": the user explicitly asks to replace '
            "or set the notes for one shipment. This is a write action and "
            "requires confirmation. Do not use this route for merely reading "
            "or summarizing existing notes.\n\n"
            "Important write-action rules:\n"
            "- Never execute an action yourself. You only classify and extract "
            "the requested action.\n"
            "- Use a write route only when the user clearly requests a data "
            "change. Questions, suggestions, and hypothetical statements are "
            "read-only.\n"
            "- A shipment can be identified by UUID, tracking number, or "
            "reference. Copy the identifier exactly as provided. Never invent "
            "or normalize identifiers.\n"
            "- For transition_shipment_status, target_status must be exactly "
            f"one of these values: {statuses}.\n"
            "- For update_shipment_notes, shipment_notes must contain only the "
            "new notes requested by the user. Never add extra facts.\n"
            "- Do not route requests to delete shipments or make unsupported "
            "writes as an action. Use direct_answer to explain that the "
            "requested action is not available through the AI agent.\n\n"
            "Read-routing rules:\n"
            "- Asking only for one shipment's current status is get_shipment.\n"
            "- Comparing two or more shipments is get_shipments.\n"
            "- Operational problems, delays, risks, or anomalies use "
            "analyze_shipment_operations.\n"
            "- Explicit summaries or timeline overviews use summarize_shipment.\n\n"
            "Return JSON only. No markdown and no explanation.\n\n"
            "Valid shapes:\n"
            '{"route":"direct_answer","shipment_identifier":null,'
            '"shipment_identifiers":[]}\n'
            '{"route":"get_shipment","shipment_identifier":"<identifier>",'
            '"shipment_identifiers":[]}\n'
            '{"route":"get_shipments","shipment_identifier":null,'
            '"shipment_identifiers":["<identifier1>","<identifier2>"]}\n'
            '{"route":"summarize_shipment",'
            '"shipment_identifier":"<identifier>","shipment_identifiers":[]}\n'
            '{"route":"analyze_shipment_operations",'
            '"shipment_identifier":"<identifier>","shipment_identifiers":[]}\n'
            '{"route":"retrieve_context","shipment_identifier":null,'
            '"shipment_identifiers":[]}\n'
            '{"route":"transition_shipment_status",'
            '"shipment_identifier":"<identifier>",'
            '"target_status":"<status>","shipment_identifiers":[]}\n'
            '{"route":"update_shipment_notes",'
            '"shipment_identifier":"<identifier>",'
            '"shipment_notes":"<new notes>","shipment_identifiers":[]}'
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
        supported_routes: tuple[AgentRoute, ...] = (
            "direct_answer",
            "get_shipment",
            "get_shipments",
            "summarize_shipment",
            "analyze_shipment_operations",
            "retrieve_context",
            "transition_shipment_status",
            "update_shipment_notes",
        )

        if route_value in supported_routes:
            return route_value

        raise AgentPlanningError("Agent planner returned an unsupported route")

    @staticmethod
    def _parse_shipment_identifier(
        value: object,
    ) -> str:
        if not isinstance(value, str):
            raise AgentPlanningError("Shipment identifier is required for shipment route")

        shipment_identifier = value.strip()

        if not shipment_identifier:
            raise AgentPlanningError("Shipment identifier is required for shipment route")

        return shipment_identifier

    @staticmethod
    def _parse_shipment_identifiers(
        value: object,
    ) -> tuple[str, ...]:
        if not isinstance(value, list):
            raise AgentPlanningError("Shipment identifiers are required for multi-shipment route")

        identifiers: list[str] = []

        for item in value:
            if not isinstance(item, str):
                raise AgentPlanningError("Shipment identifiers must be strings")

            identifier = item.strip()

            if not identifier:
                raise AgentPlanningError("Shipment identifiers must not be empty")

            identifiers.append(identifier)

        if not (MIN_MULTI_SHIPMENT_COUNT <= len(identifiers) <= MAX_MULTI_SHIPMENT_COUNT):
            raise AgentPlanningError(
                "Multi-shipment requests require between "
                f"{MIN_MULTI_SHIPMENT_COUNT} and "
                f"{MAX_MULTI_SHIPMENT_COUNT} shipment identifiers"
            )

        if len(set(identifiers)) != len(identifiers):
            raise AgentPlanningError("Multi-shipment identifiers must be unique")

        return tuple(identifiers)

    @staticmethod
    def _parse_target_status(
        value: object,
    ) -> ShipmentStatus:
        if not isinstance(value, str):
            raise AgentPlanningError("Target shipment status is required for transition action")

        normalized = value.strip()

        try:
            return ShipmentStatus(normalized)
        except ValueError as exc:
            raise AgentPlanningError(
                "Agent planner returned an unsupported target shipment status"
            ) from exc

    @staticmethod
    def _parse_shipment_notes(
        value: object,
    ) -> str:
        if not isinstance(value, str):
            raise AgentPlanningError("Shipment notes are required for notes update action")

        notes = " ".join(value.split())

        if not notes:
            raise AgentPlanningError("Shipment notes must not be empty")

        if len(notes) > MAX_AI_NOTES_LENGTH:
            raise AgentPlanningError(
                f"Shipment notes must not exceed {MAX_AI_NOTES_LENGTH} characters"
            )

        return notes

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
        payload = cls._decode_json(json_content)

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
