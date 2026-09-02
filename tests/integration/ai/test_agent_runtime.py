from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.dependencies import build_agent_runtime
from app.core.config import get_settings


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_runtime_direct_answer_with_real_llm(
    db_session: AsyncSession,
) -> None:
    settings = get_settings()

    runtime = build_agent_runtime(
        settings=settings,
        session=db_session,
    )

    answer = await runtime.execute(
        tenant_id=uuid4(),
        question=(
            "Briefly explain what a shipment tracking number is. "
            "Do not look up a specific shipment."
        ),
    )

    assert answer.strip()
