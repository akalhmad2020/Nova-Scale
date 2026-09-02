from uuid import uuid4

import pytest

from app.ai.application.agent.decision import AgentDecision
from app.ai.application.agent.exceptions import AgentPlanningError
from app.ai.application.services.generate_text import GenerateTextService
from app.ai.domain.models import LLMResponse
from app.ai.infrastructure.agent.llm_agent_planner import (
    LLMAgentPlanner,
)
from tests.unit.ai.fakes import FakeLLMProvider


@pytest.mark.asyncio
async def test_llm_agent_planner_selects_direct_answer() -> None:
    llm_provider = FakeLLMProvider()
    llm_provider.response = LLMResponse(
        content='{"route":"direct_answer","shipment_id":null}',
        model="fake-model",
    )

    planner = LLMAgentPlanner(
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        )
    )

    decision = await planner.plan(
        question="What can NovaScale help me with?",
    )

    assert decision.route == "direct_answer"
    assert decision.shipment_id is None

    assert len(llm_provider.requests) == 1
    assert llm_provider.requests[0].temperature == 0.0


@pytest.mark.asyncio
async def test_llm_agent_planner_selects_get_shipment() -> None:
    shipment_id = uuid4()

    llm_provider = FakeLLMProvider()
    llm_provider.response = LLMResponse(
        content=(f'{{"route":"get_shipment","shipment_id":"{shipment_id}"}}'),
        model="fake-model",
    )

    planner = LLMAgentPlanner(
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        )
    )

    decision = await planner.plan(
        question=f"Where is shipment {shipment_id}?",
    )

    assert decision.route == "get_shipment"
    assert decision.shipment_id == shipment_id


@pytest.mark.asyncio
async def test_llm_agent_planner_accepts_json_inside_code_fence() -> None:
    llm_provider = FakeLLMProvider()
    llm_provider.response = LLMResponse(
        content=('```json\n{"route":"direct_answer","shipment_id":null}\n```'),
        model="fake-model",
    )

    planner = LLMAgentPlanner(
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        )
    )

    decision = await planner.plan(
        question="Hello",
    )

    assert decision.route == "direct_answer"
    assert decision.shipment_id is None


@pytest.mark.asyncio
async def test_llm_agent_planner_rejects_invalid_route() -> None:
    llm_provider = FakeLLMProvider()
    llm_provider.response = LLMResponse(
        content='{"route":"delete_shipment","shipment_id":null}',
        model="fake-model",
    )

    planner = LLMAgentPlanner(
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        )
    )

    with pytest.raises(
        AgentPlanningError,
        match="unsupported route",
    ):
        await planner.plan(
            question="Delete my shipment",
        )


@pytest.mark.asyncio
async def test_llm_agent_planner_requires_shipment_id_for_lookup() -> None:
    llm_provider = FakeLLMProvider()
    llm_provider.response = LLMResponse(
        content='{"route":"get_shipment","shipment_id":null}',
        model="fake-model",
    )

    planner = LLMAgentPlanner(
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        )
    )

    with pytest.raises(
        AgentPlanningError,
        match="Shipment id is required",
    ):
        await planner.plan(
            question="Where is my shipment?",
        )


@pytest.mark.asyncio
async def test_llm_agent_planner_rejects_invalid_json() -> None:
    llm_provider = FakeLLMProvider()
    llm_provider.response = LLMResponse(
        content="I think you should use get_shipment.",
        model="fake-model",
    )

    planner = LLMAgentPlanner(
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        )
    )

    with pytest.raises(
        AgentPlanningError,
        match="did not return a JSON object",
    ):
        await planner.plan(
            question="Where is my shipment?",
        )


@pytest.mark.asyncio
async def test_planner_selects_retrieve_context_route() -> None:
    provider = FakeLLMProvider()
    provider.response = LLMResponse(
        content=('{"route":"retrieve_context","shipment_id":null}'),
        model="fake-model",
    )

    planner = LLMAgentPlanner(
        generate_text_service=GenerateTextService(
            provider=provider,
        ),
    )

    decision = await planner.plan(
        question="What does our shipping policy say about insurance?",
    )

    assert decision == AgentDecision(
        route="retrieve_context",
        shipment_id=None,
    )
