from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.ai.application.agent.shipment_summary_models import (
    ShipmentEventSummary,
    ShipmentSummaryContext,
)
from app.ai.application.agent.shipment_summary_tool import ShipmentSummaryTool
from app.ai.application.services.generate_text import GenerateTextService
from app.ai.application.services.summarize_shipment import (
    SummarizeShipmentService,
)
from tests.unit.ai.fakes import FakeLLMProvider


@pytest.mark.asyncio
async def test_summarize_shipment_uses_grounded_shipment_context() -> None:
    tenant_id = uuid4()
    shipment_id = uuid4()
    customer_id = uuid4()
    origin_location_id = uuid4()
    destination_location_id = uuid4()
    event_location_id = uuid4()

    event = ShipmentEventSummary(
        id=uuid4(),
        event_type="departed_location",
        status="in_transit",
        location_id=event_location_id,
        description="Shipment departed the distribution center.",
        occurred_at=datetime(
            2026,
            9,
            1,
            12,
            30,
            tzinfo=UTC,
        ),
        metadata={
            "source": "carrier",
        },
    )

    context = ShipmentSummaryContext(
        shipment_id=shipment_id,
        tenant_id=tenant_id,
        tracking_number="NS-TRACK-001",
        reference="CUSTOMER-REF-001",
        status="in_transit",
        service_type="express",
        description="Electronics shipment",
        weight=Decimal("12.500"),
        weight_unit="kg",
        notes="Handle carefully",
        customer_id=customer_id,
        origin_location_id=origin_location_id,
        destination_location_id=destination_location_id,
        event_count=1,
        latest_event=event,
        events=(event,),
    )

    shipment_summary_tool = AsyncMock(
        spec=ShipmentSummaryTool,
    )
    shipment_summary_tool.execute.return_value = context

    llm_provider = FakeLLMProvider()

    generate_text_service = GenerateTextService(
        provider=llm_provider,
    )

    service = SummarizeShipmentService(
        shipment_summary_tool=shipment_summary_tool,
        generate_text_service=generate_text_service,
    )

    response = await service.execute(
        tenant_id=tenant_id,
        shipment_id=shipment_id,
    )

    assert response.content == "fake response"
    assert response.model == "fake-model"

    shipment_summary_tool.execute.assert_awaited_once_with(
        tenant_id=tenant_id,
        shipment_id=shipment_id,
    )

    assert len(llm_provider.requests) == 1

    request = llm_provider.requests[0]

    assert request.temperature == 0.0
    assert request.max_tokens == 96
    assert request.context_window == 2048

    assert len(request.messages) == 2

    system_message = request.messages[0]
    user_message = request.messages[1]

    assert system_message.role == "system"
    assert "Do not invent" in system_message.content

    assert user_message.role == "user"

    prompt = user_message.content

    assert str(shipment_id) in prompt
    assert "NS-TRACK-001" in prompt
    assert "CUSTOMER-REF-001" in prompt
    assert "status=in_transit" in prompt
    assert "service=express" in prompt
    assert "description=Electronics shipment" in prompt
    assert "weight=12.500 kg" in prompt
    assert "notes=Handle carefully" in prompt
    assert "event_count=1" in prompt
    assert "latest_event=" in prompt

    assert "type=departed_location" in prompt
    assert "status=in_transit" in prompt
    assert "Shipment departed the distribution center." in prompt

    assert str(customer_id) not in prompt
    assert str(origin_location_id) not in prompt
    assert str(destination_location_id) not in prompt
    assert str(event_location_id) not in prompt
    assert "metadata=" not in prompt


@pytest.mark.asyncio
async def test_summarize_shipment_handles_empty_timeline() -> None:
    tenant_id = uuid4()
    shipment_id = uuid4()

    context = ShipmentSummaryContext(
        shipment_id=shipment_id,
        tenant_id=tenant_id,
        tracking_number="NS-TRACK-EMPTY",
        reference=None,
        status="draft",
        service_type="standard",
        description=None,
        weight=Decimal("5.000"),
        weight_unit="kg",
        notes=None,
        customer_id=uuid4(),
        origin_location_id=uuid4(),
        destination_location_id=uuid4(),
        event_count=0,
        latest_event=None,
        events=(),
    )

    shipment_summary_tool = AsyncMock(
        spec=ShipmentSummaryTool,
    )
    shipment_summary_tool.execute.return_value = context

    llm_provider = FakeLLMProvider()

    generate_text_service = GenerateTextService(
        provider=llm_provider,
    )

    service = SummarizeShipmentService(
        shipment_summary_tool=shipment_summary_tool,
        generate_text_service=generate_text_service,
    )

    await service.execute(
        tenant_id=tenant_id,
        shipment_id=shipment_id,
    )

    assert len(llm_provider.requests) == 1

    request = llm_provider.requests[0]

    assert request.temperature == 0.0
    assert request.max_tokens == 96
    assert request.context_window == 2048

    prompt = request.messages[-1].content

    assert str(shipment_id) in prompt
    assert "NS-TRACK-EMPTY" in prompt
    assert "reference=none" in prompt
    assert "status=draft" in prompt
    assert "service=standard" in prompt
    assert "description=none" in prompt
    assert "weight=5.000 kg" in prompt
    assert "notes=none" in prompt
    assert "event_count=0" in prompt
    assert "latest_event=none" in prompt
    assert "Timeline:\nnone" in prompt
