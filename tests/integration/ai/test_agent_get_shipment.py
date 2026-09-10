from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

import app.core.database  # noqa: F401
from app.ai.application.agent.decision import AgentDecision
from app.ai.application.dependencies import build_agent_runtime
from app.ai.application.services.generate_text import GenerateTextService
from app.core.config import get_settings
from app.core.tenant_context import (
    reset_current_tenant_id,
    set_current_tenant_id,
)
from app.modules.customers.domain.enums import CustomerStatus
from app.modules.customers.infrastructure.models.customer import Customer
from app.modules.identity.domain.enums import TenantStatus
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.permission import Permission
from app.modules.identity.infrastructure.models.role import Role
from app.modules.identity.infrastructure.models.role_permission import (
    RolePermission,
)
from app.modules.identity.infrastructure.models.tenant import Tenant
from app.modules.locations.domain.enums import (
    LocationStatus,
    LocationType,
)
from app.modules.locations.infrastructure.models.location import Location
from app.modules.shipments.application.exceptions import (
    ShipmentNotFoundError,
)
from app.modules.shipments.domain.enums import (
    ServiceType,
    ShipmentStatus,
    WeightUnit,
)
from app.modules.shipments.infrastructure.models.shipment import Shipment
from tests.unit.ai.fakes import (
    FakeAgentPlanner,
    FakeLLMProvider,
)


async def set_session_tenant_context(
    session: AsyncSession,
    tenant_id: UUID,
) -> None:
    await session.execute(
        text(
            """
            SELECT set_config(
                'app.current_tenant_id',
                :tenant_id,
                true
            )
            """
        ),
        {"tenant_id": str(tenant_id)},
    )


async def create_role_with_permission(
    *,
    session: AsyncSession,
    permission_code: str,
) -> UUID:
    permission = await session.scalar(
        select(Permission).where(
            Permission.code == permission_code,
        )
    )

    if permission is None:
        permission = Permission(
            code=permission_code,
            description=f"Integration test permission: {permission_code}",
        )

        session.add(permission)
        await session.flush()

    role = Role(
        name=f"ai-integration-role-{uuid4()}",
        description="AI integration test role",
    )

    session.add(role)
    await session.flush()

    session.add(
        RolePermission(
            role_id=role.id,
            permission_id=permission.id,
        )
    )

    await session.flush()

    return role.id


@pytest.mark.integration
@pytest.mark.external_ai
@pytest.mark.asyncio
async def test_agent_gets_real_shipment_with_real_llm(
    db_session: AsyncSession,
) -> None:
    unique = uuid4()

    tenant = Tenant(
        name="Agent Integration Tenant",
        slug=f"agent-integration-{unique}",
        status=TenantStatus.ACTIVE,
    )

    db_session.add(tenant)
    await db_session.flush()

    await set_session_tenant_context(
        db_session,
        tenant.id,
    )

    customer = Customer(
        tenant_id=tenant.id,
        name="Agent Integration Customer",
        code=f"AGENT-CUSTOMER-{unique}",
        status=CustomerStatus.ACTIVE,
    )

    origin = Location(
        tenant_id=tenant.id,
        name="Agent Origin",
        code=f"AGENT-ORIGIN-{unique}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Ramallah",
        address_line1="Agent Origin Address",
        status=LocationStatus.ACTIVE,
    )

    destination = Location(
        tenant_id=tenant.id,
        name="Agent Destination",
        code=f"AGENT-DEST-{unique}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Nablus",
        address_line1="Agent Destination Address",
        status=LocationStatus.ACTIVE,
    )

    db_session.add_all(
        [
            customer,
            origin,
            destination,
        ]
    )

    await db_session.flush()

    shipment = Shipment(
        tenant_id=tenant.id,
        customer_id=customer.id,
        origin_location_id=origin.id,
        destination_location_id=destination.id,
        tracking_number=f"AGENT-{unique}",
        reference="AGENT-REF-001",
        status=ShipmentStatus.IN_TRANSIT,
        service_type=ServiceType.EXPRESS,
        description="Agent integration shipment",
        weight=Decimal("12.500"),
        weight_unit=WeightUnit.KG,
        notes="Handle carefully",
    )

    db_session.add(shipment)
    await db_session.commit()

    role_id = await create_role_with_permission(
        session=db_session,
        permission_code=Permissions.SHIPMENT_READ,
    )

    await db_session.commit()

    settings = get_settings()

    runtime = build_agent_runtime(
        settings=settings,
        session=db_session,
    )

    await set_session_tenant_context(
        db_session,
        tenant.id,
    )

    tenant_context_token = set_current_tenant_id(
        tenant.id,
    )

    try:
        answer = await runtime.execute(
            tenant_id=tenant.id,
            role_id=role_id,
            question=(
                f"Look up shipment with UUID {shipment.id} "
                "and tell me its tracking number and current status."
            ),
        )
    finally:
        reset_current_tenant_id(
            tenant_context_token,
        )

    assert answer.strip()

    normalized_answer = answer.lower()

    assert str(shipment.id).lower() in normalized_answer

    expected_status = shipment.status.value.lower()
    expected_status_natural = expected_status.replace(
        "_",
        " ",
    )

    assert expected_status in normalized_answer or expected_status_natural in normalized_answer


@pytest.mark.integration
@pytest.mark.external_ai
@pytest.mark.asyncio
async def test_agent_cannot_access_shipment_from_another_tenant(
    db_session: AsyncSession,
) -> None:
    unique = uuid4()

    owner_tenant = Tenant(
        name="Agent Owner Tenant",
        slug=f"agent-owner-{unique}",
        status=TenantStatus.ACTIVE,
    )

    foreign_tenant = Tenant(
        name="Agent Foreign Tenant",
        slug=f"agent-foreign-{unique}",
        status=TenantStatus.ACTIVE,
    )

    db_session.add_all(
        [
            owner_tenant,
            foreign_tenant,
        ]
    )

    await db_session.flush()

    await set_session_tenant_context(
        db_session,
        owner_tenant.id,
    )

    customer = Customer(
        tenant_id=owner_tenant.id,
        name="Agent Isolation Customer",
        code=f"AGENT-ISOLATION-CUSTOMER-{unique}",
        status=CustomerStatus.ACTIVE,
    )

    origin = Location(
        tenant_id=owner_tenant.id,
        name="Agent Isolation Origin",
        code=f"AGENT-ISOLATION-ORIGIN-{unique}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Ramallah",
        address_line1="Agent Isolation Origin Address",
        status=LocationStatus.ACTIVE,
    )

    destination = Location(
        tenant_id=owner_tenant.id,
        name="Agent Isolation Destination",
        code=f"AGENT-ISOLATION-DEST-{unique}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Nablus",
        address_line1="Agent Isolation Destination Address",
        status=LocationStatus.ACTIVE,
    )

    db_session.add_all(
        [
            customer,
            origin,
            destination,
        ]
    )

    await db_session.flush()

    shipment = Shipment(
        tenant_id=owner_tenant.id,
        customer_id=customer.id,
        origin_location_id=origin.id,
        destination_location_id=destination.id,
        tracking_number=f"AGENT-ISOLATION-{unique}",
        reference="AGENT-ISOLATION-REF",
        status=ShipmentStatus.IN_TRANSIT,
        service_type=ServiceType.EXPRESS,
        description="Agent tenant isolation shipment",
        weight=Decimal("8.000"),
        weight_unit=WeightUnit.KG,
        notes=None,
    )

    db_session.add(shipment)
    await db_session.commit()

    role_id = await create_role_with_permission(
        session=db_session,
        permission_code=Permissions.SHIPMENT_READ,
    )

    await db_session.commit()

    settings = get_settings()

    runtime = build_agent_runtime(
        settings=settings,
        session=db_session,
    )

    await set_session_tenant_context(
        db_session,
        foreign_tenant.id,
    )

    tenant_context_token = set_current_tenant_id(
        foreign_tenant.id,
    )

    try:
        with pytest.raises(ShipmentNotFoundError):
            await runtime.execute(
                tenant_id=foreign_tenant.id,
                role_id=role_id,
                question=(
                    f"Look up shipment with UUID {shipment.id} and tell me its current status."
                ),
            )
    finally:
        reset_current_tenant_id(
            tenant_context_token,
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_returns_clarification_for_ambiguous_shipment_reference(
    db_session: AsyncSession,
) -> None:
    unique = uuid4()

    tenant = Tenant(
        name="Agent Ambiguous Reference Tenant",
        slug=f"agent-ambiguous-{unique}",
        status=TenantStatus.ACTIVE,
    )

    db_session.add(tenant)
    await db_session.flush()

    await set_session_tenant_context(
        db_session,
        tenant.id,
    )

    customer = Customer(
        tenant_id=tenant.id,
        name="Agent Ambiguous Customer",
        code=f"AGENT-AMBIGUOUS-CUSTOMER-{unique}",
        status=CustomerStatus.ACTIVE,
    )

    origin = Location(
        tenant_id=tenant.id,
        name="Agent Ambiguous Origin",
        code=f"AGENT-AMBIGUOUS-ORIGIN-{unique}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Ramallah",
        address_line1="Agent Ambiguous Origin Address",
        status=LocationStatus.ACTIVE,
    )

    destination = Location(
        tenant_id=tenant.id,
        name="Agent Ambiguous Destination",
        code=f"AGENT-AMBIGUOUS-DEST-{unique}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Nablus",
        address_line1="Agent Ambiguous Destination Address",
        status=LocationStatus.ACTIVE,
    )

    db_session.add_all(
        [
            customer,
            origin,
            destination,
        ]
    )

    await db_session.flush()

    shared_reference = f"AMBIGUOUS-REF-{unique}"

    first_shipment = Shipment(
        tenant_id=tenant.id,
        customer_id=customer.id,
        origin_location_id=origin.id,
        destination_location_id=destination.id,
        tracking_number=f"AMBIGUOUS-SHIP-1-{unique}",
        reference=shared_reference,
        status=ShipmentStatus.IN_TRANSIT,
        service_type=ServiceType.EXPRESS,
        description="First ambiguous shipment",
        weight=Decimal("10.000"),
        weight_unit=WeightUnit.KG,
        notes=None,
    )

    second_shipment = Shipment(
        tenant_id=tenant.id,
        customer_id=customer.id,
        origin_location_id=origin.id,
        destination_location_id=destination.id,
        tracking_number=f"AMBIGUOUS-SHIP-2-{unique}",
        reference=shared_reference,
        status=ShipmentStatus.IN_TRANSIT,
        service_type=ServiceType.EXPRESS,
        description="Second ambiguous shipment",
        weight=Decimal("12.000"),
        weight_unit=WeightUnit.KG,
        notes=None,
    )

    db_session.add_all(
        [
            first_shipment,
            second_shipment,
        ]
    )

    await db_session.commit()

    role_id = await create_role_with_permission(
        session=db_session,
        permission_code=Permissions.SHIPMENT_READ,
    )

    await db_session.commit()

    settings = get_settings()

    runtime = build_agent_runtime(
        settings=settings,
        session=db_session,
    )

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="get_shipment",
        shipment_identifier=shared_reference,
    )

    runtime._agent_planner = planner

    await set_session_tenant_context(
        db_session,
        tenant.id,
    )

    tenant_context_token = set_current_tenant_id(
        tenant.id,
    )

    try:
        answer = await runtime.execute(
            tenant_id=tenant.id,
            role_id=role_id,
            question=(f"Where is shipment {shared_reference}?"),
        )
    finally:
        reset_current_tenant_id(
            tenant_context_token,
        )

    assert answer == (
        f"I found multiple shipments matching "
        f"'{shared_reference}'. "
        "Please provide the shipment tracking number or UUID "
        "so I can identify the correct shipment."
    )

    assert planner.questions == [
        f"Where is shipment {shared_reference}?",
    ]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_gets_multiple_shipments_from_database(
    db_session: AsyncSession,
) -> None:
    unique = uuid4()

    tenant = Tenant(
        name="Agent Multi Shipment Tenant",
        slug=f"agent-multi-shipment-{unique}",
        status=TenantStatus.ACTIVE,
    )

    db_session.add(tenant)
    await db_session.flush()

    await set_session_tenant_context(
        db_session,
        tenant.id,
    )

    customer = Customer(
        tenant_id=tenant.id,
        name="Agent Multi Shipment Customer",
        code=f"AGENT-MULTI-CUSTOMER-{unique}",
        status=CustomerStatus.ACTIVE,
    )

    origin = Location(
        tenant_id=tenant.id,
        name="Agent Multi Origin",
        code=f"AGENT-MULTI-ORIGIN-{unique}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Ramallah",
        address_line1="Agent Multi Origin Address",
        status=LocationStatus.ACTIVE,
    )

    destination = Location(
        tenant_id=tenant.id,
        name="Agent Multi Destination",
        code=f"AGENT-MULTI-DEST-{unique}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Nablus",
        address_line1="Agent Multi Destination Address",
        status=LocationStatus.ACTIVE,
    )

    db_session.add_all(
        [
            customer,
            origin,
            destination,
        ]
    )
    await db_session.flush()

    first_tracking_number = f"MULTI-001-{unique}"
    second_tracking_number = f"MULTI-002-{unique}"

    first_shipment = Shipment(
        tenant_id=tenant.id,
        customer_id=customer.id,
        origin_location_id=origin.id,
        destination_location_id=destination.id,
        tracking_number=first_tracking_number,
        reference=f"MULTI-REF-001-{unique}",
        status=ShipmentStatus.IN_TRANSIT,
        service_type=ServiceType.EXPRESS,
        description="First multi-shipment integration shipment",
        weight=Decimal("10.000"),
        weight_unit=WeightUnit.KG,
        notes=None,
    )

    second_shipment = Shipment(
        tenant_id=tenant.id,
        customer_id=customer.id,
        origin_location_id=origin.id,
        destination_location_id=destination.id,
        tracking_number=second_tracking_number,
        reference=f"MULTI-REF-002-{unique}",
        status=ShipmentStatus.DELIVERED,
        service_type=ServiceType.EXPRESS,
        description="Second multi-shipment integration shipment",
        weight=Decimal("20.000"),
        weight_unit=WeightUnit.KG,
        notes=None,
    )

    db_session.add_all(
        [
            first_shipment,
            second_shipment,
        ]
    )
    await db_session.commit()

    role_id = await create_role_with_permission(
        session=db_session,
        permission_code=Permissions.SHIPMENT_READ,
    )
    await db_session.commit()

    settings = get_settings()

    runtime = build_agent_runtime(
        settings=settings,
        session=db_session,
    )

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="get_shipments",
        shipment_identifiers=(
            first_tracking_number,
            second_tracking_number,
        ),
    )

    runtime._agent_planner = planner

    llm_provider = FakeLLMProvider()

    runtime._generate_text_service = GenerateTextService(
        provider=llm_provider,
    )

    await set_session_tenant_context(
        db_session,
        tenant.id,
    )

    tenant_context_token = set_current_tenant_id(
        tenant.id,
    )

    try:
        answer = await runtime.execute(
            tenant_id=tenant.id,
            role_id=role_id,
            question=(f"Compare {first_tracking_number} and {second_tracking_number}."),
        )
    finally:
        reset_current_tenant_id(
            tenant_context_token,
        )

    assert answer == "fake response"

    assert planner.questions == [(f"Compare {first_tracking_number} and {second_tracking_number}.")]

    assert len(llm_provider.requests) == 1

    request = llm_provider.requests[0]

    assert request.temperature == 0.0

    prompt = request.messages[-1].content

    assert first_tracking_number in prompt
    assert second_tracking_number in prompt

    assert str(first_shipment.id) in prompt
    assert str(second_shipment.id) in prompt

    assert prompt.count("Resolution status: resolved") == 2

    first_position = prompt.index(
        first_tracking_number,
    )
    second_position = prompt.index(
        second_tracking_number,
    )

    assert first_position < second_position


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_multi_shipment_cannot_access_shipment_from_another_tenant(
    db_session: AsyncSession,
) -> None:
    unique = uuid4()

    tenant = Tenant(
        name="Agent Multi Owner Tenant",
        slug=f"agent-multi-owner-{unique}",
        status=TenantStatus.ACTIVE,
    )

    foreign_tenant = Tenant(
        name="Agent Multi Foreign Tenant",
        slug=f"agent-multi-foreign-{unique}",
        status=TenantStatus.ACTIVE,
    )

    db_session.add_all(
        [
            tenant,
            foreign_tenant,
        ]
    )
    await db_session.flush()

    await set_session_tenant_context(
        db_session,
        tenant.id,
    )

    customer = Customer(
        tenant_id=tenant.id,
        name="Agent Multi Isolation Customer",
        code=f"AGENT-MULTI-ISOLATION-CUSTOMER-{unique}",
        status=CustomerStatus.ACTIVE,
    )

    origin = Location(
        tenant_id=tenant.id,
        name="Agent Multi Isolation Origin",
        code=f"AGENT-MULTI-ISOLATION-ORIGIN-{unique}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Ramallah",
        address_line1="Agent Multi Isolation Origin Address",
        status=LocationStatus.ACTIVE,
    )

    destination = Location(
        tenant_id=tenant.id,
        name="Agent Multi Isolation Destination",
        code=f"AGENT-MULTI-ISOLATION-DEST-{unique}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Nablus",
        address_line1="Agent Multi Isolation Destination Address",
        status=LocationStatus.ACTIVE,
    )

    db_session.add_all(
        [
            customer,
            origin,
            destination,
        ]
    )
    await db_session.flush()

    visible_tracking_number = f"MULTI-VISIBLE-{unique}"

    visible_shipment = Shipment(
        tenant_id=tenant.id,
        customer_id=customer.id,
        origin_location_id=origin.id,
        destination_location_id=destination.id,
        tracking_number=visible_tracking_number,
        reference=f"MULTI-VISIBLE-REF-{unique}",
        status=ShipmentStatus.IN_TRANSIT,
        service_type=ServiceType.EXPRESS,
        description="Visible multi-shipment integration shipment",
        weight=Decimal("10.000"),
        weight_unit=WeightUnit.KG,
        notes=None,
    )

    db_session.add(visible_shipment)
    await db_session.flush()

    await set_session_tenant_context(
        db_session,
        foreign_tenant.id,
    )

    foreign_customer = Customer(
        tenant_id=foreign_tenant.id,
        name="Agent Multi Foreign Customer",
        code=f"AGENT-MULTI-FOREIGN-CUSTOMER-{unique}",
        status=CustomerStatus.ACTIVE,
    )

    foreign_origin = Location(
        tenant_id=foreign_tenant.id,
        name="Agent Multi Foreign Origin",
        code=f"AGENT-MULTI-FOREIGN-ORIGIN-{unique}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Hebron",
        address_line1="Agent Multi Foreign Origin Address",
        status=LocationStatus.ACTIVE,
    )

    foreign_destination = Location(
        tenant_id=foreign_tenant.id,
        name="Agent Multi Foreign Destination",
        code=f"AGENT-MULTI-FOREIGN-DEST-{unique}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Jenin",
        address_line1="Agent Multi Foreign Destination Address",
        status=LocationStatus.ACTIVE,
    )

    db_session.add_all(
        [
            foreign_customer,
            foreign_origin,
            foreign_destination,
        ]
    )
    await db_session.flush()

    foreign_tracking_number = f"MULTI-FOREIGN-{unique}"

    foreign_shipment = Shipment(
        tenant_id=foreign_tenant.id,
        customer_id=foreign_customer.id,
        origin_location_id=foreign_origin.id,
        destination_location_id=foreign_destination.id,
        tracking_number=foreign_tracking_number,
        reference=f"MULTI-FOREIGN-REF-{unique}",
        status=ShipmentStatus.DELIVERED,
        service_type=ServiceType.EXPRESS,
        description="Foreign multi-shipment integration shipment",
        weight=Decimal("15.000"),
        weight_unit=WeightUnit.KG,
        notes=None,
    )

    db_session.add(foreign_shipment)
    await db_session.commit()

    role_id = await create_role_with_permission(
        session=db_session,
        permission_code=Permissions.SHIPMENT_READ,
    )
    await db_session.commit()

    settings = get_settings()

    runtime = build_agent_runtime(
        settings=settings,
        session=db_session,
    )

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="get_shipments",
        shipment_identifiers=(
            visible_tracking_number,
            foreign_tracking_number,
        ),
    )

    runtime._agent_planner = planner

    llm_provider = FakeLLMProvider()

    runtime._generate_text_service = GenerateTextService(
        provider=llm_provider,
    )

    await set_session_tenant_context(
        db_session,
        tenant.id,
    )

    tenant_context_token = set_current_tenant_id(
        tenant.id,
    )

    try:
        answer = await runtime.execute(
            tenant_id=tenant.id,
            role_id=role_id,
            question=(f"Compare {visible_tracking_number} and {foreign_tracking_number}."),
        )
    finally:
        reset_current_tenant_id(
            tenant_context_token,
        )

    assert answer == "fake response"

    assert planner.questions == [
        (f"Compare {visible_tracking_number} and {foreign_tracking_number}.")
    ]

    assert len(llm_provider.requests) == 1

    prompt = llm_provider.requests[0].messages[-1].content

    assert visible_tracking_number in prompt
    assert foreign_tracking_number in prompt

    assert "Resolution status: resolved" in prompt
    assert "Resolution status: not_found" in prompt

    assert str(visible_shipment.id) in prompt
    assert str(foreign_shipment.id) not in prompt

    assert "The shipment could not be found for the current tenant." in prompt


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_multi_shipment_returns_partial_result_for_ambiguous_identifier(
    db_session: AsyncSession,
) -> None:
    unique = uuid4()

    tenant = Tenant(
        name="Agent Multi Ambiguous Tenant",
        slug=f"agent-multi-ambiguous-{unique}",
        status=TenantStatus.ACTIVE,
    )

    db_session.add(tenant)
    await db_session.flush()

    await set_session_tenant_context(
        db_session,
        tenant.id,
    )

    customer = Customer(
        tenant_id=tenant.id,
        name="Agent Multi Ambiguous Customer",
        code=f"AGENT-MULTI-AMBIGUOUS-CUSTOMER-{unique}",
        status=CustomerStatus.ACTIVE,
    )

    origin = Location(
        tenant_id=tenant.id,
        name="Agent Multi Ambiguous Origin",
        code=f"AGENT-MULTI-AMBIGUOUS-ORIGIN-{unique}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Ramallah",
        address_line1="Agent Multi Ambiguous Origin Address",
        status=LocationStatus.ACTIVE,
    )

    destination = Location(
        tenant_id=tenant.id,
        name="Agent Multi Ambiguous Destination",
        code=f"AGENT-MULTI-AMBIGUOUS-DEST-{unique}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Nablus",
        address_line1="Agent Multi Ambiguous Destination Address",
        status=LocationStatus.ACTIVE,
    )

    db_session.add_all(
        [
            customer,
            origin,
            destination,
        ]
    )
    await db_session.flush()

    shared_reference = f"MULTI-AMBIGUOUS-REF-{unique}"
    unique_tracking_number = f"MULTI-UNIQUE-{unique}"

    first_ambiguous_shipment = Shipment(
        tenant_id=tenant.id,
        customer_id=customer.id,
        origin_location_id=origin.id,
        destination_location_id=destination.id,
        tracking_number=f"MULTI-AMBIGUOUS-1-{unique}",
        reference=shared_reference,
        status=ShipmentStatus.IN_TRANSIT,
        service_type=ServiceType.EXPRESS,
        description="First ambiguous multi-shipment",
        weight=Decimal("10.000"),
        weight_unit=WeightUnit.KG,
        notes=None,
    )

    second_ambiguous_shipment = Shipment(
        tenant_id=tenant.id,
        customer_id=customer.id,
        origin_location_id=origin.id,
        destination_location_id=destination.id,
        tracking_number=f"MULTI-AMBIGUOUS-2-{unique}",
        reference=shared_reference,
        status=ShipmentStatus.IN_TRANSIT,
        service_type=ServiceType.EXPRESS,
        description="Second ambiguous multi-shipment",
        weight=Decimal("12.000"),
        weight_unit=WeightUnit.KG,
        notes=None,
    )

    unique_shipment = Shipment(
        tenant_id=tenant.id,
        customer_id=customer.id,
        origin_location_id=origin.id,
        destination_location_id=destination.id,
        tracking_number=unique_tracking_number,
        reference=f"MULTI-UNIQUE-REF-{unique}",
        status=ShipmentStatus.DELIVERED,
        service_type=ServiceType.EXPRESS,
        description="Unique multi-shipment",
        weight=Decimal("15.000"),
        weight_unit=WeightUnit.KG,
        notes=None,
    )

    db_session.add_all(
        [
            first_ambiguous_shipment,
            second_ambiguous_shipment,
            unique_shipment,
        ]
    )
    await db_session.commit()

    role_id = await create_role_with_permission(
        session=db_session,
        permission_code=Permissions.SHIPMENT_READ,
    )
    await db_session.commit()

    settings = get_settings()

    runtime = build_agent_runtime(
        settings=settings,
        session=db_session,
    )

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="get_shipments",
        shipment_identifiers=(
            shared_reference,
            unique_tracking_number,
        ),
    )

    runtime._agent_planner = planner

    llm_provider = FakeLLMProvider()

    runtime._generate_text_service = GenerateTextService(
        provider=llm_provider,
    )

    await set_session_tenant_context(
        db_session,
        tenant.id,
    )

    tenant_context_token = set_current_tenant_id(
        tenant.id,
    )

    try:
        result = await runtime.execute_with_context(
            tenant_id=tenant.id,
            role_id=role_id,
            question=(f"Compare {shared_reference} and {unique_tracking_number}."),
        )
    finally:
        reset_current_tenant_id(
            tenant_context_token,
        )

    assert result.answer == "fake response"
    assert result.continuation is None

    assert planner.questions == [(f"Compare {shared_reference} and {unique_tracking_number}.")]

    assert len(llm_provider.requests) == 1

    prompt = llm_provider.requests[0].messages[-1].content

    assert f"Identifier: {shared_reference}" in prompt
    assert "Resolution status: ambiguous" in prompt

    assert f"Identifier: {unique_tracking_number}" in prompt
    assert "Resolution status: resolved" in prompt
    assert str(unique_shipment.id) in prompt

    assert str(first_ambiguous_shipment.id) not in prompt
    assert str(second_ambiguous_shipment.id) not in prompt
