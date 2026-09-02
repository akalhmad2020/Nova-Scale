from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.dependencies import build_agent_runtime
from app.core.config import get_settings
from app.modules.customers.domain.enums import CustomerStatus
from app.modules.customers.infrastructure.models.customer import Customer
from app.modules.identity.domain.enums import TenantStatus
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


@pytest.mark.integration
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

    settings = get_settings()

    runtime = build_agent_runtime(
        settings=settings,
        session=db_session,
    )

    answer = await runtime.execute(
        tenant_id=tenant.id,
        question=(
            f"Look up shipment with UUID {shipment.id} "
            "and tell me its tracking number and current status."
        ),
    )

    assert answer.strip()

    normalized_answer = answer.lower()

    assert shipment.tracking_number.lower() in normalized_answer
    assert shipment.status.value.lower() in normalized_answer


@pytest.mark.integration
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

    settings = get_settings()

    runtime = build_agent_runtime(
        settings=settings,
        session=db_session,
    )

    with pytest.raises(ShipmentNotFoundError):
        await runtime.execute(
            tenant_id=foreign_tenant.id,
            question=(f"Look up shipment with UUID {shipment.id} and tell me its current status."),
        )
