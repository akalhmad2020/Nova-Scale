import pytest

from app.ai.application.agent.decision import AgentDecision
from app.ai.application.agent.exceptions import AgentPlanningError
from app.ai.application.services.generate_text import GenerateTextService
from app.ai.domain.models import LLMResponse
from app.ai.infrastructure.agent.llm_agent_planner import (
    LLMAgentPlanner,
)
from tests.unit.ai.fakes import FakeLLMProvider


def make_planner(
    response_content: str,
) -> tuple[LLMAgentPlanner, FakeLLMProvider]:
    provider = FakeLLMProvider()
    provider.response = LLMResponse(
        content=response_content,
        model="fake-model",
    )

    planner = LLMAgentPlanner(
        generate_text_service=GenerateTextService(
            provider=provider,
        ),
    )

    return planner, provider


@pytest.mark.asyncio
async def test_llm_agent_planner_selects_direct_answer() -> None:
    planner, provider = make_planner('{"route":"direct_answer","shipment_identifier":null}')

    decision = await planner.plan(
        question="What can NovaScale help me with?",
    )

    assert decision == AgentDecision(
        route="direct_answer",
        shipment_identifier=None,
    )

    assert len(provider.requests) == 1
    assert provider.requests[0].temperature == 0.0


@pytest.mark.asyncio
async def test_llm_agent_planner_selects_get_shipment_by_tracking_number() -> None:
    planner, _ = make_planner('{"route":"get_shipment","shipment_identifier":"SHIP-001"}')

    decision = await planner.plan(
        question="Where is shipment SHIP-001?",
    )

    assert decision == AgentDecision(
        route="get_shipment",
        shipment_identifier="SHIP-001",
    )


@pytest.mark.asyncio
async def test_llm_agent_planner_selects_get_shipment_by_reference() -> None:
    planner, _ = make_planner('{"route":"get_shipment","shipment_identifier":"ORDER-100"}')

    decision = await planner.plan(
        question="Where is shipment ORDER-100?",
    )

    assert decision == AgentDecision(
        route="get_shipment",
        shipment_identifier="ORDER-100",
    )


@pytest.mark.asyncio
async def test_llm_agent_planner_accepts_uuid_as_identifier() -> None:
    shipment_id = "6e9d40d1-7ef2-49b9-bc48-59d07cb0b339"

    planner, _ = make_planner(f'{{"route":"get_shipment","shipment_identifier":"{shipment_id}"}}')

    decision = await planner.plan(
        question=f"Where is shipment {shipment_id}?",
    )

    assert decision == AgentDecision(
        route="get_shipment",
        shipment_identifier=shipment_id,
    )


@pytest.mark.asyncio
async def test_llm_agent_planner_accepts_json_inside_code_fence() -> None:
    planner, _ = make_planner('```json\n{"route":"direct_answer","shipment_identifier":null}\n```')

    decision = await planner.plan(
        question="Hello",
    )

    assert decision == AgentDecision(
        route="direct_answer",
        shipment_identifier=None,
    )


@pytest.mark.asyncio
async def test_llm_agent_planner_rejects_invalid_route() -> None:
    planner, _ = make_planner('{"route":"delete_shipment","shipment_identifier":null}')

    with pytest.raises(
        AgentPlanningError,
        match="unsupported route",
    ):
        await planner.plan(
            question="Delete my shipment",
        )


@pytest.mark.asyncio
async def test_llm_agent_planner_requires_identifier_for_lookup() -> None:
    planner, _ = make_planner('{"route":"get_shipment","shipment_identifier":null}')

    with pytest.raises(
        AgentPlanningError,
        match="Shipment identifier is required",
    ):
        await planner.plan(
            question="Where is my shipment?",
        )


@pytest.mark.asyncio
async def test_llm_agent_planner_rejects_empty_identifier() -> None:
    planner, _ = make_planner('{"route":"get_shipment","shipment_identifier":"   "}')

    with pytest.raises(
        AgentPlanningError,
        match="Shipment identifier is required",
    ):
        await planner.plan(
            question="Where is my shipment?",
        )


@pytest.mark.asyncio
async def test_llm_agent_planner_rejects_invalid_json() -> None:
    planner, _ = make_planner("I think you should use get_shipment.")

    with pytest.raises(
        AgentPlanningError,
        match="did not return a JSON object",
    ):
        await planner.plan(
            question="Where is my shipment?",
        )


@pytest.mark.asyncio
async def test_planner_selects_retrieve_context_route() -> None:
    planner, _ = make_planner('{"route":"retrieve_context","shipment_identifier":null}')

    decision = await planner.plan(
        question="What does our shipping policy say about insurance?",
    )

    assert decision == AgentDecision(
        route="retrieve_context",
        shipment_identifier=None,
    )


@pytest.mark.asyncio
async def test_llm_agent_planner_selects_summarize_shipment() -> None:
    planner, _ = make_planner('{"route":"summarize_shipment","shipment_identifier":"SHIP-001"}')

    decision = await planner.plan(
        question="Summarize shipment SHIP-001.",
    )

    assert decision == AgentDecision(
        route="summarize_shipment",
        shipment_identifier="SHIP-001",
    )


@pytest.mark.asyncio
async def test_llm_agent_planner_requires_identifier_for_summary() -> None:
    planner, _ = make_planner('{"route":"summarize_shipment","shipment_identifier":null}')

    with pytest.raises(
        AgentPlanningError,
        match="Shipment identifier is required",
    ):
        await planner.plan(
            question="Summarize my shipment.",
        )


@pytest.mark.asyncio
async def test_llm_agent_planner_selects_operational_analysis() -> None:
    planner, _ = make_planner(
        '{"route":"analyze_shipment_operations","shipment_identifier":"SHIP-001"}'
    )

    decision = await planner.plan(
        question="Is there anything wrong with shipment SHIP-001?",
    )

    assert decision == AgentDecision(
        route="analyze_shipment_operations",
        shipment_identifier="SHIP-001",
    )


@pytest.mark.asyncio
async def test_llm_agent_planner_requires_identifier_for_operational_analysis() -> None:
    planner, _ = make_planner('{"route":"analyze_shipment_operations","shipment_identifier":null}')

    with pytest.raises(
        AgentPlanningError,
        match="Shipment identifier is required",
    ):
        await planner.plan(
            question="Analyze my shipment for operational problems.",
        )


@pytest.mark.asyncio
async def test_llm_agent_planner_repairs_escaped_colon_before_null() -> None:
    planner, _ = make_planner('{"route":"direct_answer","shipment_identifier\\:null}')

    decision = await planner.plan(
        question="What is a shipment tracking number?",
    )

    assert decision == AgentDecision(
        route="direct_answer",
        shipment_identifier=None,
    )
