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
from app.modules.rates.domain.enums import RateQuoteStatus
from app.modules.rates.infrastructure.models.rate_quote import RateQuote
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
                await session.execute(delete(RateQuote).where(RateQuote.tenant_id.in_(tenant_ids)))

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

    password_hasher = Argon2PasswordHasher()

    try:
        async with session_factory() as session:
            user = User(
                email=email,
                password_hash=password_hasher.hash(password),
                first_name="Rate",
                last_name="Reader",
                is_active=True,
            )

            tenant = Tenant(
                name="Rates Read Integration Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Rates read integration role",
            )

            permission = await session.scalar(
                select(Permission).where(Permission.code == Permissions.RATE_READ)
            )

            if permission is None:
                permission = Permission(
                    code=Permissions.RATE_READ,
                    description="Read rate quotes",
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
                name="Rate Read Customer",
                code=f"RATE-READ-CUST-{uuid4()}",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Rate Read Origin",
                code=f"RATE-READ-ORIGIN-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Ramallah",
                address_line1="Rate Read Origin Address",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Rate Read Destination",
                code=f"RATE-READ-DEST-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Nablus",
                address_line1="Rate Read Destination Address",
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
                tracking_number=f"RATE-READ-SHIP-{uuid4()}",
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

            return tenant, shipment

    finally:
        await engine.dispose()


async def create_foreign_context(
    *,
    tenant_slug: str,
) -> tuple[Tenant, Shipment, RateQuote]:
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
                name="Foreign Rates Read Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            session.add(tenant)
            await session.flush()

            customer = Customer(
                tenant_id=tenant.id,
                name="Foreign Rate Read Customer",
                code=f"FOREIGN-RATE-READ-CUST-{uuid4()}",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Foreign Rate Read Origin",
                code=f"FOREIGN-RATE-READ-ORIGIN-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Hebron",
                address_line1="Foreign Rate Read Origin Address",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Foreign Rate Read Destination",
                code=f"FOREIGN-RATE-READ-DEST-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Jenin",
                address_line1="Foreign Rate Read Destination Address",
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
                tracking_number=f"FOREIGN-RATE-READ-SHIP-{uuid4()}",
                status=ShipmentStatus.DRAFT,
                service_type=ServiceType.STANDARD,
                weight=Decimal("12.000"),
                weight_unit=WeightUnit.KG,
            )

            session.add(shipment)
            await session.flush()

            rate_quote = RateQuote(
                tenant_id=tenant.id,
                shipment_id=shipment.id,
                currency="USD",
                base_amount=Decimal("100.00"),
                surcharge_amount=Decimal("10.00"),
                total_amount=Decimal("110.00"),
                status=RateQuoteStatus.DRAFT,
                expires_at=None,
            )

            session.add(rate_quote)
            await session.commit()

            return tenant, shipment, rate_quote

    finally:
        await engine.dispose()


async def create_rate_quote(
    *,
    tenant_id: UUID,
    shipment_id: UUID,
    currency: str,
    base_amount: str,
    surcharge_amount: str,
    status: RateQuoteStatus = RateQuoteStatus.DRAFT,
) -> RateQuote:
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
            base = Decimal(base_amount)
            surcharge = Decimal(surcharge_amount)

            rate_quote = RateQuote(
                tenant_id=tenant_id,
                shipment_id=shipment_id,
                currency=currency,
                base_amount=base,
                surcharge_amount=surcharge,
                total_amount=base + surcharge,
                status=status,
                expires_at=None,
            )

            session.add(rate_quote)
            await session.commit()

            return rate_quote

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
async def test_list_rate_quotes_endpoint_returns_shipment_quotes() -> None:
    unique = uuid4()

    email = f"rate-read-list-{unique}@example.com"
    password = "very-secure-rate-password"
    tenant_slug = f"rate-read-list-tenant-{unique}"
    role_name = f"rate-read-list-role-{unique}"

    tenant, shipment = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        first = await create_rate_quote(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            currency="USD",
            base_amount="100.00",
            surcharge_amount="10.00",
        )

        second = await create_rate_quote(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            currency="USD",
            base_amount="200.00",
            surcharge_amount="20.00",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/rates",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 2

        returned_ids = {item["id"] for item in body}

        assert returned_ids == {
            str(first.id),
            str(second.id),
        }

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_list_rate_quotes_endpoint_returns_empty_list() -> None:
    unique = uuid4()

    email = f"rate-read-empty-{unique}@example.com"
    password = "very-secure-rate-password"
    tenant_slug = f"rate-read-empty-tenant-{unique}"
    role_name = f"rate-read-empty-role-{unique}"

    tenant, shipment = await create_read_context(
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
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/rates",
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
async def test_list_rate_quotes_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"rate-read-denied-{unique}@example.com"
    password = "very-secure-rate-password"
    tenant_slug = f"rate-read-denied-tenant-{unique}"
    role_name = f"rate-read-denied-role-{unique}"

    tenant, shipment = await create_read_context(
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
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/rates",
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
async def test_list_rate_quotes_endpoint_rejects_foreign_shipment() -> None:
    unique = uuid4()

    email = f"rate-read-foreign-shipment-{unique}@example.com"
    password = "very-secure-rate-password"

    tenant_slug = f"rate-read-isolation-tenant-{unique}"
    foreign_slug = f"rate-read-foreign-tenant-{unique}"
    role_name = f"rate-read-isolation-role-{unique}"

    tenant, _ = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    _, foreign_shipment, _ = await create_foreign_context(
        tenant_slug=foreign_slug,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/shipments/{foreign_shipment.id}/rates",
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


@pytest.mark.integration
async def test_get_rate_quote_endpoint_returns_quote() -> None:
    unique = uuid4()

    email = f"rate-get-{unique}@example.com"
    password = "very-secure-rate-password"
    tenant_slug = f"rate-get-tenant-{unique}"
    role_name = f"rate-get-role-{unique}"

    tenant, shipment = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        quote = await create_rate_quote(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            currency="USD",
            base_amount="100.00",
            surcharge_amount="15.50",
            status=RateQuoteStatus.QUOTED,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/rates/{quote.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(quote.id)
        assert body["tenant_id"] == str(tenant.id)
        assert body["shipment_id"] == str(shipment.id)

        assert body["currency"] == "USD"
        assert body["base_amount"] == "100.00"
        assert body["surcharge_amount"] == "15.50"
        assert body["total_amount"] == "115.50"
        assert body["status"] == "quoted"

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_get_rate_quote_endpoint_rejects_unknown_quote() -> None:
    unique = uuid4()

    email = f"rate-get-missing-{unique}@example.com"
    password = "very-secure-rate-password"
    tenant_slug = f"rate-get-missing-tenant-{unique}"
    role_name = f"rate-get-missing-role-{unique}"

    tenant, _ = await create_read_context(
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
                f"/api/v1/tenants/{tenant.id}/rates/{uuid4()}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 404
        assert response.json() == {"detail": "Rate quote not found"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_get_rate_quote_endpoint_rejects_foreign_quote() -> None:
    unique = uuid4()

    email = f"rate-get-foreign-{unique}@example.com"
    password = "very-secure-rate-password"

    tenant_slug = f"rate-get-tenant-{unique}"
    foreign_slug = f"rate-get-foreign-tenant-{unique}"
    role_name = f"rate-get-foreign-role-{unique}"

    tenant, _ = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    _, _, foreign_quote = await create_foreign_context(
        tenant_slug=foreign_slug,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/rates/{foreign_quote.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 404
        assert response.json() == {"detail": "Rate quote not found"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(
                tenant_slug,
                foreign_slug,
            ),
            role_name=role_name,
        )
