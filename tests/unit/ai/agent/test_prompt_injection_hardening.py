from app.ai.infrastructure.agent.llm_agent_planner import LLMAgentPlanner


def test_planner_system_prompt_keeps_write_safety_authoritative() -> None:
    prompt = LLMAgentPlanner._build_system_prompt()

    assert "Never execute an action yourself" in prompt
    assert "requires confirmation" in prompt
    assert "Never invent" in prompt
