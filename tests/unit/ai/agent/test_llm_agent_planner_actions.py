from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.application.agent.exceptions import AgentPlanningError
from app.ai.application.services.generate_text import GenerateTextService
from app.ai.domain.models import LLMResponse
from app.ai.infrastructure.agent.llm_agent_planner import LLMAgentPlanner
from app.modules.shipments.domain.enums import ShipmentStatus


def make_planner(response_content: str) -> LLMAgentPlanner:
    service = MagicMock(spec=GenerateTextService)
    service.execute = AsyncMock(
        return_value=LLMResponse(
            content=response_content,
            model="fake-model",
        )
    )

    return LLMAgentPlanner(
        generate_text_service=cast(GenerateTextService, service),
    )


@pytest.mark.asyncio
async def test_planner_selects_status_transition_write_action() -> None:
    target = next(iter(ShipmentStatus))
    planner = make_planner(
        "{"
        '"route":"transition_shipment_status",'
        '"shipment_identifier":"SHIP-001",'
        f'"target_status":"{target.value}",'
        '"shipment_identifiers":[]'
        "}"
    )

    decision = await planner.plan(
        question="Move SHIP-001 to the requested status.",
    )

    assert decision.route == "transition_shipment_status"
    assert decision.shipment_identifier == "SHIP-001"
    assert decision.target_shipment_status == target


@pytest.mark.asyncio
async def test_planner_selects_notes_update_write_action() -> None:
    planner = make_planner(
        "{"
        '"route":"update_shipment_notes",'
        '"shipment_identifier":"SHIP-001",'
        '"shipment_notes":"Keep upright",'
        '"shipment_identifiers":[]'
        "}"
    )

    decision = await planner.plan(
        question="Set SHIP-001 notes to Keep upright.",
    )

    assert decision.route == "update_shipment_notes"
    assert decision.shipment_identifier == "SHIP-001"
    assert decision.shipment_notes == "Keep upright"


@pytest.mark.asyncio
async def test_planner_rejects_invalid_target_status() -> None:
    planner = make_planner(
        "{"
        '"route":"transition_shipment_status",'
        '"shipment_identifier":"SHIP-001",'
        '"target_status":"not-a-status",'
        '"shipment_identifiers":[]'
        "}"
    )

    with pytest.raises(AgentPlanningError):
        await planner.plan(
            question="Move SHIP-001 somewhere impossible.",
        )
