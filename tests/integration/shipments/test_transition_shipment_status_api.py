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
from app.modules.audit.domain.enums import AuditActorType, AuditOutcome
from app.modules.audit.infrastructure.models.audit_log import AuditLog
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
            user_id = await session.scalar(
                select(User.id).where(
                    User.email == email,
                )
            )

            tenant_ids = list(
                (
                    await session.scalars(
                        select(Tenant.id).where(
                            Tenant.slug.in_(tenant_slugs),
                        )
                    )
                ).all()
            )

            role_id = await session.scalar(
                select(Role.id).where(
                    Role.name == role_name,
                )
            )

            if tenant_ids:
                await session.execute(
        delete(AuditLog).where(
            AuditLog.tenant_id.in_(tenant_ids),
        )
    )

                await session.execute(
        delete(ShipmentEvent).where(
            ShipmentEvent.tenant_id.in_(tenant_ids),
        )
    )

                await session.execute(
        delete(Shipment).where(
            Shipment.tenant_id.in_(tenant_ids),
        )
    )

                await session.execute(
        delete(Customer).where(
            Customer.tenant_id.in_(tenant_ids),
        )
    )

                await session.execute(
        delete(Location).where(
            Location.tenant_id.in_(tenant_ids),
        )
    )
            if user_id is not None:
                await session.execute(
                    delete(AuthSession).where(
                        AuthSession.user_id == user_id,
                    )
                )

                await session.execute(
                    delete(Membership).where(
                        Membership.user_id == user_id,
                    )
                )

            if tenant_ids:
                await session.execute(
                    delete(Membership).where(
                        Membership.tenant_id.in_(tenant_ids),
                    )
                )

            if role_id is not None:
                await session.execute(
                    delete(RolePermission).where(
                        RolePermission.role_id == role_id,
                    )
                )

            if user_id is not None:
                await session.execute(
                    delete(User).where(
                        User.id == user_id,
                    )
                )

            if tenant_ids:
                await session.execute(
                    delete(Tenant).where(
                        Tenant.id.in_(tenant_ids),
                    )
                )

            if role_id is not None:
                await session.execute(
                    delete(Role).where(
                        Role.id == role_id,
                    )
                )

            await session.commit()

    finally:
        await engine.dispose()


async def create_transition_context(
    *,
    email: str,
    password: str,
    tenant_slug: str,
    role_name: str,
    assign_permission: bool,
) -> tuple[
    Tenant,
    Customer,
    Location,
    Location,
    User,
]:
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
                last_name="Transitioner",
                is_active=True,
            )

            tenant = Tenant(
                name="Shipment Transition Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Shipment transition integration role",
            )

            permission = await session.scalar(
                select(Permission).where(
                    Permission.code == Permissions.SHIPMENT_TRANSITION,
                )
            )

            if permission is None:
                permission = Permission(
                    code=Permissions.SHIPMENT_TRANSITION,
                    description="Transition shipment status",
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
                name="Transition Customer",
                code="TRANS-CUST-001",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Transition Origin",
                code="TRANS-ORIGIN",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Ramallah",
                address_line1="Origin Address",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Transition Destination",
                code="TRANS-DEST",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Nablus",
                address_line1="Destination Address",
                status=LocationStatus.ACTIVE,
            )

            session.add_all(
                [
                    customer,
                    origin,
                    destination,
                ]
            )

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
                customer,
                origin,
                destination,
                user,
            )

    finally:
        await engine.dispose()


async def create_foreign_resources(
    *,
    tenant_slug: str,
) -> tuple[
    Tenant,
    Customer,
    Location,
    Location,
]:
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
                name="Foreign Shipment Transition Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            session.add(tenant)
            await session.flush()

            customer = Customer(
                tenant_id=tenant.id,
                name="Foreign Transition Customer",
                code="FOREIGN-CUST",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Foreign Transition Origin",
                code="FOREIGN-ORIGIN",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Hebron",
                address_line1="Foreign Origin Address",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Foreign Transition Destination",
                code="FOREIGN-DEST",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Jenin",
                address_line1="Foreign Destination Address",
                status=LocationStatus.ACTIVE,
            )

            session.add_all(
                [
                    customer,
                    origin,
                    destination,
                ]
            )

            await session.commit()

            return (
                tenant,
                customer,
                origin,
                destination,
            )

    finally:
        await engine.dispose()


async def create_shipment(
    *,
    tenant_id: UUID,
    customer_id: UUID,
    origin_location_id: UUID,
    destination_location_id: UUID,
    tracking_number: str,
    status: ShipmentStatus = ShipmentStatus.DRAFT,
) -> Shipment:
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
            shipment = Shipment(
                tenant_id=tenant_id,
                customer_id=customer_id,
                origin_location_id=origin_location_id,
                destination_location_id=destination_location_id,
                tracking_number=tracking_number,
                status=status,
                service_type=ServiceType.STANDARD,
                weight=Decimal("1.000"),
                weight_unit=WeightUnit.KG,
            )

            session.add(shipment)
            await session.commit()

            return shipment

    finally:
        await engine.dispose()


async def get_shipment_status_audit_logs(
    *,
    tenant_id: UUID,
    shipment_id: UUID | None = None,
) -> list[AuditLog]:
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
            statement = (
                select(AuditLog)
                .where(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.action == "shipment.status_changed",
                    AuditLog.resource_type == "shipment",
                )
                .order_by(
                    AuditLog.occurred_at.asc(),
                    AuditLog.created_at.asc(),
                )
            )

            if shipment_id is not None:
                statement = statement.where(
                    AuditLog.resource_id == shipment_id,
                )

            return list(
                (
                    await session.scalars(
                        statement,
                    )
                ).all()
            )

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
async def test_transition_shipment_endpoint_completes_full_lifecycle() -> None:
    unique = uuid4()

    email = f"shipment-transition-{unique}@example.com"
    password = "very-secure-shipment-password"
    tenant_slug = f"shipment-transition-tenant-{unique}"
    role_name = f"shipment-transition-role-{unique}"

    (
        tenant,
        customer,
        origin,
        destination,
        user,
    ) = await create_transition_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        shipment = await create_shipment(
            tenant_id=tenant.id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
            tracking_number="LIFECYCLE-001",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            ready_response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/transition",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "status": "ready",
                },
            )

            assert ready_response.status_code == 200
            assert ready_response.json()["status"] == "ready"

            transit_response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/transition",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "status": "in_transit",
                },
            )

            assert transit_response.status_code == 200
            assert transit_response.json()["status"] == "in_transit"

            delivered_response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/transition",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "status": "delivered",
                },
            )

            assert delivered_response.status_code == 200
            assert delivered_response.json()["status"] == "delivered"

        audit_logs = await get_shipment_status_audit_logs(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
        )

        assert len(audit_logs) == 3

        first_audit = audit_logs[0]

        assert first_audit.tenant_id == tenant.id
        assert first_audit.actor_type == AuditActorType.USER
        assert first_audit.actor_id == user.id
        assert first_audit.action == "shipment.status_changed"
        assert first_audit.resource_type == "shipment"
        assert first_audit.resource_id == shipment.id
        assert first_audit.outcome == AuditOutcome.SUCCESS
        assert first_audit.metadata_ == {
            "tracking_number": shipment.tracking_number,
            "previous_status": ShipmentStatus.DRAFT.value,
            "new_status": ShipmentStatus.READY.value,
        }
        assert first_audit.occurred_at is not None

        second_audit = audit_logs[1]

        assert second_audit.actor_id == user.id
        assert second_audit.metadata_ == {
            "tracking_number": shipment.tracking_number,
            "previous_status": ShipmentStatus.READY.value,
            "new_status": ShipmentStatus.IN_TRANSIT.value,
        }

        third_audit = audit_logs[2]

        assert third_audit.actor_id == user.id
        assert third_audit.metadata_ == {
            "tracking_number": shipment.tracking_number,
            "previous_status": ShipmentStatus.IN_TRANSIT.value,
            "new_status": ShipmentStatus.DELIVERED.value,
        }

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
@pytest.mark.parametrize(
    ("initial_status", "target_status"),
    [
        (
            ShipmentStatus.DRAFT,
            ShipmentStatus.CANCELLED,
        ),
        (
            ShipmentStatus.READY,
            ShipmentStatus.CANCELLED,
        ),
    ],
)
async def test_transition_shipment_endpoint_allows_cancellation(
    initial_status: ShipmentStatus,
    target_status: ShipmentStatus,
) -> None:
    unique = uuid4()

    email = f"shipment-cancel-{unique}@example.com"
    password = "very-secure-shipment-password"
    tenant_slug = f"shipment-cancel-tenant-{unique}"
    role_name = f"shipment-cancel-role-{unique}"

    (
        tenant,
        customer,
        origin,
        destination,
        user,
    ) = await create_transition_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        shipment = await create_shipment(
            tenant_id=tenant.id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
            tracking_number=f"CANCEL-{unique}",
            status=initial_status,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/transition",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "status": target_status.value,
                },
            )

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

        audit_logs = await get_shipment_status_audit_logs(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
        )

        assert len(audit_logs) == 1

        audit_log = audit_logs[0]

        assert audit_log.tenant_id == tenant.id
        assert audit_log.actor_type == AuditActorType.USER
        assert audit_log.actor_id == user.id
        assert audit_log.action == "shipment.status_changed"
        assert audit_log.resource_type == "shipment"
        assert audit_log.resource_id == shipment.id
        assert audit_log.outcome == AuditOutcome.SUCCESS
        assert audit_log.metadata_ == {
            "tracking_number": shipment.tracking_number,
            "previous_status": initial_status.value,
            "new_status": ShipmentStatus.CANCELLED.value,
        }
        assert audit_log.occurred_at is not None

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
@pytest.mark.parametrize(
    ("initial_status", "target_status"),
    [
        (
            ShipmentStatus.DRAFT,
            ShipmentStatus.DELIVERED,
        ),
        (
            ShipmentStatus.DELIVERED,
            ShipmentStatus.DRAFT,
        ),
        (
            ShipmentStatus.CANCELLED,
            ShipmentStatus.IN_TRANSIT,
        ),
    ],
)
async def test_transition_shipment_endpoint_rejects_invalid_transition(
    initial_status: ShipmentStatus,
    target_status: ShipmentStatus,
) -> None:
    unique = uuid4()

    email = f"shipment-invalid-transition-{unique}@example.com"
    password = "very-secure-shipment-password"
    tenant_slug = f"shipment-invalid-transition-{unique}"
    role_name = f"shipment-invalid-transition-role-{unique}"

    (
        tenant,
        customer,
        origin,
        destination,
        _,
    ) = await create_transition_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        shipment = await create_shipment(
            tenant_id=tenant.id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
            tracking_number=f"INVALID-{unique}",
            status=initial_status,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/transition",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "status": target_status.value,
                },
            )

        assert response.status_code == 422
        assert response.json() == {
            "detail": "Invalid shipment status transition",
        }

        audit_logs = await get_shipment_status_audit_logs(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
        )

        assert audit_logs == []

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_transition_shipment_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"shipment-transition-denied-{unique}@example.com"
    password = "very-secure-shipment-password"
    tenant_slug = f"shipment-transition-denied-{unique}"
    role_name = f"shipment-transition-denied-role-{unique}"

    (
        tenant,
        customer,
        origin,
        destination,
        _,
    ) = await create_transition_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=False,
    )

    try:
        shipment = await create_shipment(
            tenant_id=tenant.id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
            tracking_number="TRANSITION-DENIED-001",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/transition",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "status": "ready",
                },
            )

        assert response.status_code == 403
        assert response.json() == {
            "detail": "Permission denied",
        }

        audit_logs = await get_shipment_status_audit_logs(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
        )

        assert audit_logs == []

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_transition_shipment_endpoint_rejects_unknown_shipment() -> None:
    unique = uuid4()

    email = f"shipment-transition-missing-{unique}@example.com"
    password = "very-secure-shipment-password"
    tenant_slug = f"shipment-transition-missing-{unique}"
    role_name = f"shipment-transition-missing-role-{unique}"

    tenant, _, _, _, _ = await create_transition_context(
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

        missing_shipment_id = uuid4()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{missing_shipment_id}/transition",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "status": "ready",
                },
            )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Shipment not found",
        }

        audit_logs = await get_shipment_status_audit_logs(
            tenant_id=tenant.id,
            shipment_id=missing_shipment_id,
        )

        assert audit_logs == []

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_transition_shipment_endpoint_rejects_other_tenant_shipment() -> None:
    unique = uuid4()

    email = f"shipment-transition-isolation-{unique}@example.com"
    password = "very-secure-shipment-password"

    tenant_slug = f"shipment-transition-isolation-{unique}"
    foreign_slug = f"shipment-transition-foreign-{unique}"
    role_name = f"shipment-transition-isolation-role-{unique}"

    tenant, _, _, _, _ = await create_transition_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    (
        foreign_tenant,
        foreign_customer,
        foreign_origin,
        foreign_destination,
    ) = await create_foreign_resources(
        tenant_slug=foreign_slug,
    )

    try:
        foreign_shipment = await create_shipment(
            tenant_id=foreign_tenant.id,
            customer_id=foreign_customer.id,
            origin_location_id=foreign_origin.id,
            destination_location_id=foreign_destination.id,
            tracking_number="FOREIGN-TRANSITION-001",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{foreign_shipment.id}/transition",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "status": "ready",
                },
            )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Shipment not found",
        }

        tenant_audit_logs = await get_shipment_status_audit_logs(
            tenant_id=tenant.id,
        )

        assert tenant_audit_logs == []

        foreign_audit_logs = await get_shipment_status_audit_logs(
            tenant_id=foreign_tenant.id,
            shipment_id=foreign_shipment.id,
        )

        assert foreign_audit_logs == []

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(
                tenant_slug,
                foreign_slug,
            ),
            role_name=role_name,
        )
