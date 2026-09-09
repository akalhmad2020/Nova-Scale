from uuid import UUID

from app.ai.application.agent.shipment_summary_models import (
    ShipmentEventSummary,
    ShipmentSummaryContext,
)
from app.ai.application.agent.shipment_summary_tool import ShipmentSummaryTool
from app.ai.application.services.generate_text import GenerateTextService
from app.ai.domain.models import LLMResponse


class SummarizeShipmentService:
    def __init__(
        self,
        *,
        shipment_summary_tool: ShipmentSummaryTool,
        generate_text_service: GenerateTextService,
    ) -> None:
        self._shipment_summary_tool = shipment_summary_tool
        self._generate_text_service = generate_text_service

    async def execute(
        self,
        *,
        tenant_id: UUID,
        shipment_id: UUID,
    ) -> LLMResponse:
        context = await self._shipment_summary_tool.execute(
            tenant_id=tenant_id,
            shipment_id=shipment_id,
        )

        return await self._generate_text_service.execute(
            prompt=self._build_prompt(context),
            system_prompt=(
                "You are the NovaScale shipment intelligence assistant. "
                "Use only the facts provided. "
                "Write a short operational summary in no more than "
                "three sentences. "
                "State the current status and latest important event. "
                "Do not invent information."
            ),
            temperature=0.0,
            max_tokens=96,
            context_window=2048,
        )

    @classmethod
    def _build_prompt(
        cls,
        context: ShipmentSummaryContext,
    ) -> str:
        timeline = cls._build_event_context(
            context.events,
        )

        latest_event = (
            cls._format_event(context.latest_event) if context.latest_event is not None else "none"
        )

        return (
            "Shipment:\n"
            f"id={context.shipment_id}\n"
            f"tracking_number={context.tracking_number}\n"
            f"reference={context.reference or 'none'}\n"
            f"status={context.status}\n"
            f"service={context.service_type}\n"
            f"description={context.description or 'none'}\n"
            f"weight={context.weight} {context.weight_unit}\n"
            f"notes={context.notes or 'none'}\n"
            f"event_count={context.event_count}\n"
            f"latest_event={latest_event}\n\n"
            "Timeline:\n"
            f"{timeline}"
        )

    @classmethod
    def _build_event_context(
        cls,
        events: tuple[ShipmentEventSummary, ...],
    ) -> str:
        if not events:
            return "none"

        return "\n".join(
            f"{index}. {cls._format_event(event)}"
            for index, event in enumerate(
                events,
                start=1,
            )
        )

    @staticmethod
    def _format_event(
        event: ShipmentEventSummary,
    ) -> str:
        parts = [
            f"time={event.occurred_at.isoformat()}",
            f"type={event.event_type}",
        ]

        if event.status is not None:
            parts.append(f"status={event.status}")

        if event.description is not None:
            parts.append(f"description={event.description}")

        return ", ".join(parts)
