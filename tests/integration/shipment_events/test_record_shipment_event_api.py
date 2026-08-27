from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.main import app
from app.modules.customers.domain.enums import CustomerStatus
from app.modules.customers.infrastructure.models.customer import Customer
from app.modules.identity.domain.enums import (
    MembershipStatus,
    TenantStatus,
)
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.auth_session import AuthSession
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.permission import Permission
from app.modules.identity.infrastructure.models.role import Role
from app.modules.identity.infrastructure.models.role_permission import (
    RolePermission,
)
from app.modules.identity.infrastructure.models.tenant import Tenant
from app.modules.identity.infrastructure.models.user import User
from app.modules.identity.infrastructure.security.password_hasher import (
    Argon2PasswordHasher,
)
from app.modules.locations.domain.enums import (
    LocationStatus,
    LocationType,
)
from app.modules.locations.infrastructure.models.location import Location
from app.modules.shipment_events.domain.enums import ShipmentEventType
from app.modules.shipment_events.infrastructure.models.shipment_event import (
    ShipmentEvent,
)
from app.modules.shipments.domain.enums import (
    ServiceType,
    ShipmentStatus,
    WeightUnit,
)
from app.modules.shipments.infrastructure.models.shipment import Shipment


async def cleanup_test_data(
    *,
    email: str,
    tenant_slugs: tuple[str, ...],
    role_name: str,
) -> None:
    settings = get_settings()

    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    try:
        async with session_factory() as session:
            user_id = await session.scalar(select(User.id).where(User.email == email))

            tenant_ids = list(
                (
                    await session.scalars(select(Tenant.id).where(Tenant.slug.in_(tenant_slugs)))
                ).all()
            )

            role_id = await session.scalar(select(Role.id).where(Role.name == role_name))

            if tenant_ids:
                await session.execute(
                    delete(ShipmentEvent).where(ShipmentEvent.tenant_id.in_(tenant_ids))
                )

                await session.execute(delete(Shipment).where(Shipment.tenant_id.in_(tenant_ids)))

                await session.execute(delete(Customer).where(Customer.tenant_id.in_(tenant_ids)))

                await session.execute(delete(Location).where(Location.tenant_id.in_(tenant_ids)))

            if user_id is not None:
                await session.execute(delete(AuthSession).where(AuthSession.user_id == user_id))

                await session.execute(delete(Membership).where(Membership.user_id == user_id))

            if tenant_ids:
                await session.execute(
                    delete(Membership).where(Membership.tenant_id.in_(tenant_ids))
                )

            if role_id is not None:
                await session.execute(
                    delete(RolePermission).where(RolePermission.role_id == role_id)
                )

            if user_id is not None:
                await session.execute(delete(User).where(User.id == user_id))

            if tenant_ids:
                await session.execute(delete(Tenant).where(Tenant.id.in_(tenant_ids)))

            if role_id is not None:
                await session.execute(delete(Role).where(Role.id == role_id))

            await session.commit()

    finally:
        await engine.dispose()


async def create_read_context(
    *,
    email: str,
    password: str,
    tenant_slug: str,
    role_name: str,
    assign_permission: bool,
) -> tuple[Tenant, Shipment, Location, User]:
    settings = get_settings()

    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    password_hasher = Argon2PasswordHasher()

    try:
        async with session_factory() as session:
            user = User(
                email=email,
                password_hash=password_hasher.hash(password),
                first_name="Shipment",
                last_name="Event Reader",
                is_active=True,
            )

            tenant = Tenant(
                name="Shipment Events Read Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Shipment events read integration role",
            )

            permission = await session.scalar(
                select(Permission).where(Permission.code == Permissions.SHIPMENT_EVENT_READ)
            )

            if permission is None:
                permission = Permission(
                    code=Permissions.SHIPMENT_EVENT_READ,
                    description="Read shipment events",
                )
                session.add(permission)

            session.add_all(
                [
                    user,
                    tenant,
                    role,
                ]
            )

            await session.flush()

            customer = Customer(
                tenant_id=tenant.id,
                name="Shipment Event Read Customer",
                code=f"EVENT-READ-CUST-{uuid4()}",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Event Read Origin",
                code=f"EVENT-READ-ORIGIN-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Ramallah",
                address_line1="Event Read Origin Address",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Event Read Destination",
                code=f"EVENT-READ-DEST-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Nablus",
                address_line1="Event Read Destination Address",
                status=LocationStatus.ACTIVE,
            )

            event_location = Location(
                tenant_id=tenant.id,
                name="Event Read Hub",
                code=f"EVENT-READ-HUB-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Jericho",
                address_line1="Event Read Hub Address",
                status=LocationStatus.ACTIVE,
            )

            session.add_all(
                [
                    customer,
                    origin,
                    destination,
                    event_location,
                ]
            )

            await session.flush()

            shipment = Shipment(
                tenant_id=tenant.id,
                customer_id=customer.id,
                origin_location_id=origin.id,
                destination_location_id=destination.id,
                tracking_number=f"EVENT-READ-SHIP-{uuid4()}",
                status=ShipmentStatus.DRAFT,
                service_type=ServiceType.STANDARD,
                weight=Decimal("10.000"),
                weight_unit=WeightUnit.KG,
            )

            session.add(shipment)

            session.add(
                Membership(
                    tenant_id=tenant.id,
                    user_id=user.id,
                    role_id=role.id,
                    status=MembershipStatus.ACTIVE,
                )
            )

            if assign_permission:
                session.add(
                    RolePermission(
                        role_id=role.id,
                        permission_id=permission.id,
                    )
                )

            await session.commit()

            return (
                tenant,
                shipment,
                event_location,
                user,
            )

    finally:
        await engine.dispose()


async def create_foreign_context(
    *,
    tenant_slug: str,
) -> tuple[Tenant, Shipment]:
    settings = get_settings()

    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    try:
        async with session_factory() as session:
            tenant = Tenant(
                name="Foreign Shipment Events Read Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            session.add(tenant)
            await session.flush()

            customer = Customer(
                tenant_id=tenant.id,
                name="Foreign Event Read Customer",
                code=f"FOREIGN-EVENT-READ-CUST-{uuid4()}",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Foreign Event Read Origin",
                code=f"FOREIGN-EVENT-READ-ORIGIN-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Hebron",
                address_line1="Foreign Event Read Origin Address",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Foreign Event Read Destination",
                code=f"FOREIGN-EVENT-READ-DEST-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Jenin",
                address_line1="Foreign Event Read Destination Address",
                status=LocationStatus.ACTIVE,
            )

            session.add_all(
                [
                    customer,
                    origin,
                    destination,
                ]
            )

            await session.flush()

            shipment = Shipment(
                tenant_id=tenant.id,
                customer_id=customer.id,
                origin_location_id=origin.id,
                destination_location_id=destination.id,
                tracking_number=f"FOREIGN-EVENT-READ-SHIP-{uuid4()}",
                status=ShipmentStatus.DRAFT,
                service_type=ServiceType.STANDARD,
                weight=Decimal("12.000"),
                weight_unit=WeightUnit.KG,
            )

            session.add(shipment)
            await session.commit()

            return (
                tenant,
                shipment,
            )

    finally:
        await engine.dispose()


async def create_event(
    *,
    tenant_id: UUID,
    shipment_id: UUID,
    event_type: ShipmentEventType,
    occurred_at: datetime,
    status: ShipmentStatus | None = None,
    location_id: UUID | None = None,
    description: str | None = None,
    metadata: dict[str, object] | None = None,
    created_by_user_id: UUID | None = None,
) -> ShipmentEvent:
    settings = get_settings()

    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    try:
        async with session_factory() as session:
            event = ShipmentEvent(
                tenant_id=tenant_id,
                shipment_id=shipment_id,
                event_type=event_type,
                status=status,
                location_id=location_id,
                description=description,
                occurred_at=occurred_at,
                metadata_=metadata,
                created_by_user_id=created_by_user_id,
            )

            session.add(event)
            await session.commit()

            return event

    finally:
        await engine.dispose()


def login_and_get_access_token(
    *,
    email: str,
    password: str,
) -> str:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

    assert response.status_code == 200

    access_token = response.json()["access_token"]

    assert isinstance(access_token, str)

    return access_token


@pytest.mark.integration
async def test_list_shipment_events_endpoint_returns_timeline_in_order() -> None:
    unique = uuid4()

    email = f"shipment-event-read-{unique}@example.com"
    password = "very-secure-shipment-event-password"
    tenant_slug = f"shipment-event-read-tenant-{unique}"
    role_name = f"shipment-event-read-role-{unique}"

    (
        tenant,
        shipment,
        location,
        user,
    ) = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        base_time = datetime.now(UTC)

        later = await create_event(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            event_type=ShipmentEventType.ARRIVED_AT_LOCATION,
            occurred_at=base_time + timedelta(hours=2),
            status=ShipmentStatus.IN_TRANSIT,
            location_id=location.id,
            description="Arrived at hub",
            metadata={
                "sequence": 3,
            },
            created_by_user_id=user.id,
        )

        first = await create_event(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            event_type=ShipmentEventType.CREATED,
            occurred_at=base_time,
            description="Shipment created",
            metadata={
                "sequence": 1,
            },
            created_by_user_id=user.id,
        )

        middle = await create_event(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            event_type=ShipmentEventType.PICKED_UP,
            occurred_at=base_time + timedelta(hours=1),
            status=ShipmentStatus.IN_TRANSIT,
            location_id=location.id,
            description="Shipment picked up",
            metadata={
                "sequence": 2,
            },
            created_by_user_id=user.id,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/events",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 3

        assert [item["id"] for item in body] == [
            str(first.id),
            str(middle.id),
            str(later.id),
        ]

        assert [item["event_type"] for item in body] == [
            "created",
            "picked_up",
            "arrived_at_location",
        ]

        assert [item["metadata"]["sequence"] for item in body] == [
            1,
            2,
            3,
        ]

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_list_shipment_events_endpoint_returns_event_details() -> None:
    unique = uuid4()

    email = f"shipment-event-details-{unique}@example.com"
    password = "very-secure-shipment-event-password"
    tenant_slug = f"shipment-event-details-tenant-{unique}"
    role_name = f"shipment-event-details-role-{unique}"

    (
        tenant,
        shipment,
        location,
        user,
    ) = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        occurred_at = datetime.now(UTC)

        event = await create_event(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            event_type=ShipmentEventType.STATUS_CHANGED,
            occurred_at=occurred_at,
            status=ShipmentStatus.READY,
            location_id=location.id,
            description="Shipment ready",
            metadata={
                "source": "integration-test",
                "scanner": "READ-001",
            },
            created_by_user_id=user.id,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/events",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 1

        returned = body[0]

        assert returned["id"] == str(event.id)
        assert returned["tenant_id"] == str(tenant.id)
        assert returned["shipment_id"] == str(shipment.id)

        assert returned["event_type"] == "status_changed"
        assert returned["status"] == "ready"

        assert returned["location_id"] == str(location.id)
        assert returned["description"] == "Shipment ready"

        assert returned["metadata"] == {
            "source": "integration-test",
            "scanner": "READ-001",
        }

        assert returned["created_by_user_id"] == str(user.id)

        assert "metadata_" not in returned

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_list_shipment_events_endpoint_returns_empty_timeline() -> None:
    unique = uuid4()

    email = f"shipment-event-empty-{unique}@example.com"
    password = "very-secure-shipment-event-password"
    tenant_slug = f"shipment-event-empty-tenant-{unique}"
    role_name = f"shipment-event-empty-role-{unique}"

    tenant, shipment, _, _ = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/events",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200
        assert response.json() == []

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_list_shipment_events_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"shipment-event-read-denied-{unique}@example.com"
    password = "very-secure-shipment-event-password"
    tenant_slug = f"shipment-event-read-denied-tenant-{unique}"
    role_name = f"shipment-event-read-denied-role-{unique}"

    tenant, shipment, _, _ = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=False,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/events",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 403
        assert response.json() == {"detail": "Permission denied"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_list_shipment_events_endpoint_rejects_unknown_shipment() -> None:
    unique = uuid4()

    email = f"shipment-event-read-missing-{unique}@example.com"
    password = "very-secure-shipment-event-password"
    tenant_slug = f"shipment-event-read-missing-tenant-{unique}"
    role_name = f"shipment-event-read-missing-role-{unique}"

    tenant, _, _, _ = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/shipments/{uuid4()}/events",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 404
        assert response.json() == {"detail": "Shipment not found"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_list_shipment_events_endpoint_rejects_foreign_shipment() -> None:
    unique = uuid4()

    email = f"shipment-event-read-foreign-{unique}@example.com"
    password = "very-secure-shipment-event-password"

    tenant_slug = f"shipment-event-read-tenant-{unique}"
    foreign_slug = f"shipment-event-read-foreign-tenant-{unique}"
    role_name = f"shipment-event-read-foreign-role-{unique}"

    tenant, _, _, _ = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    _, foreign_shipment = await create_foreign_context(
        tenant_slug=foreign_slug,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/shipments/{foreign_shipment.id}/events",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 404
        assert response.json() == {"detail": "Shipment not found"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(
                tenant_slug,
                foreign_slug,
            ),
            role_name=role_name,
        )
