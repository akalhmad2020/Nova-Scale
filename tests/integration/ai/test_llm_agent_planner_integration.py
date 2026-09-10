from uuid import uuid4

import pytest

from app.ai.application.agent.decision import AgentDecision
from app.ai.application.services.generate_text import GenerateTextService
from app.ai.infrastructure.agent.llm_agent_planner import LLMAgentPlanner
from app.ai.infrastructure.dependencies import build_llm_provider
from app.core.config import get_settings


@pytest.mark.integration
@pytest.mark.external_ai
@pytest.mark.asyncio
async def test_real_llm_planner_selects_summarize_shipment_route() -> None:
    shipment_id = uuid4()

    settings = get_settings()

    llm_provider = build_llm_provider(
        settings,
    )

    planner = LLMAgentPlanner(
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        ),
    )

    decision = await planner.plan(
        question=(
            f"Summarize shipment with UUID {shipment_id}. "
            "Give me an operational overview including its timeline."
        ),
    )

    assert decision == AgentDecision(
        route="summarize_shipment",
        shipment_identifier=str(shipment_id),
    )


@pytest.mark.integration
@pytest.mark.external_ai
@pytest.mark.asyncio
async def test_real_llm_planner_distinguishes_lookup_from_summary() -> None:
    shipment_id = uuid4()

    settings = get_settings()

    llm_provider = build_llm_provider(
        settings,
    )

    planner = LLMAgentPlanner(
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        ),
    )

    decision = await planner.plan(
        question=(f"Look up shipment with UUID {shipment_id} and tell me its current status."),
    )

    assert decision == AgentDecision(
        route="get_shipment",
        shipment_identifier=str(shipment_id),
    )


@pytest.mark.integration
@pytest.mark.external_ai
@pytest.mark.asyncio
async def test_real_llm_planner_selects_document_context_route() -> None:
    settings = get_settings()

    llm_provider = build_llm_provider(
        settings,
    )

    planner = LLMAgentPlanner(
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        ),
    )

    decision = await planner.plan(
        question=(
            "According to our stored tenant shipping documents, "
            "what is the policy for reporting damaged cargo?"
        ),
    )

    assert decision == AgentDecision(
        route="retrieve_context",
        shipment_identifier=None,
    )
