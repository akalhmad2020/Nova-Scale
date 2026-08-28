from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
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
from app.modules.pricing.domain.enums import PricingRuleStatus
from app.modules.pricing.infrastructure.models import PricingRule
from app.modules.rates.infrastructure.models.rate_quote import RateQuote
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
                    await session.scalars(select(Tenant.id).where(Tenant.slug.in_(tenant_slugs)))
                ).all()
            )

            role_id = await session.scalar(
                select(Role.id).where(
                    Role.name == role_name,
                )
            )

            if tenant_ids:
                await session.execute(delete(RateQuote).where(RateQuote.tenant_id.in_(tenant_ids)))

                await session.execute(
                    delete(PricingRule).where(PricingRule.tenant_id.in_(tenant_ids))
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


async def create_pricing_quote_context(
    *,
    email: str,
    password: str,
    tenant_slug: str,
    role_name: str,
    assign_rate_create_permission: bool,
) -> tuple[Tenant, Customer, Location, Location]:
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
                first_name="Pricing",
                last_name="Calculator",
                is_active=True,
            )

            tenant = Tenant(
                name="Pricing Quote Integration Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Pricing quote integration role",
            )

            permission_codes = [
                Permissions.SHIPMENT_CREATE,
                Permissions.PRICING_RULE_CREATE,
            ]

            if assign_rate_create_permission:
                permission_codes.append(
                    Permissions.RATE_CREATE,
                )

            permissions: list[Permission] = []

            for permission_code in permission_codes:
                permission = await session.scalar(
                    select(Permission).where(Permission.code == permission_code)
                )

                if permission is None:
                    permission = Permission(
                        code=permission_code,
                        description=permission_code,
                    )
                    session.add(permission)

                permissions.append(permission)

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
                name="Pricing Customer",
                code=f"PRICE-{uuid4()}",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Pricing Origin",
                code=f"PRICE-ORIGIN-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Ramallah",
                address_line1="Pricing Origin Address",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Pricing Destination",
                code=f"PRICE-DEST-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Nablus",
                address_line1="Pricing Destination Address",
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

            for permission in permissions:
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
            )

    finally:
        await engine.dispose()


async def create_foreign_pricing_rule(
    *,
    tenant_slug: str,
) -> tuple[Tenant, PricingRule]:
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
                name="Foreign Pricing Quote Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            session.add(tenant)
            await session.flush()

            pricing_rule = PricingRule(
                tenant_id=tenant.id,
                name="Foreign Pricing Rule",
                service_type="express",
                currency="USD",
                base_amount=Decimal("25.00"),
                price_per_kg=Decimal("2.5000"),
                surcharge_amount=Decimal("5.00"),
                status=PricingRuleStatus.ACTIVE,
                valid_from=None,
                valid_until=None,
            )

            session.add(pricing_rule)
            await session.commit()

            return tenant, pricing_rule

    finally:
        await engine.dispose()


async def deactivate_pricing_rule(
    *,
    pricing_rule_id: UUID,
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
            pricing_rule = await session.get(
                PricingRule,
                pricing_rule_id,
            )

            assert pricing_rule is not None

            pricing_rule.status = PricingRuleStatus.INACTIVE

            await session.commit()

    finally:
        await engine.dispose()


async def get_rate_quote_from_database(
    *,
    rate_quote_id: UUID,
) -> RateQuote | None:
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
            rate_quote = await session.get(
                RateQuote,
                rate_quote_id,
            )

            if rate_quote is not None:
                session.expunge(rate_quote)

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


def create_shipment_via_api(
    *,
    access_token: str,
    tenant_id: UUID,
    customer_id: UUID,
    origin_location_id: UUID,
    destination_location_id: UUID,
    service_type: str = "express",
    weight: str = "10.000",
) -> dict[str, object]:
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/tenants/{tenant_id}/shipments",
            headers={
                "Authorization": f"Bearer {access_token}",
            },
            json={
                "customer_id": str(customer_id),
                "origin_location_id": str(origin_location_id),
                "destination_location_id": str(destination_location_id),
                "tracking_number": f"PRICING-{uuid4()}",
                "reference": "PRICING-REF",
                "service_type": service_type,
                "description": "Pricing integration shipment",
                "weight": weight,
                "weight_unit": "kg",
                "notes": "Pricing calculation test",
            },
        )

    assert response.status_code == 201

    body = response.json()

    assert isinstance(body, dict)

    return body


def create_pricing_rule_via_api(
    *,
    access_token: str,
    tenant_id: UUID,
    service_type: str = "express",
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
) -> dict[str, object]:
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/tenants/{tenant_id}/pricing-rules",
            headers={
                "Authorization": f"Bearer {access_token}",
            },
            json={
                "name": f"Pricing Rule {uuid4()}",
                "service_type": service_type,
                "currency": "USD",
                "base_amount": "25.00",
                "price_per_kg": "2.5000",
                "surcharge_amount": "5.00",
                "valid_from": (valid_from.isoformat() if valid_from is not None else None),
                "valid_until": (valid_until.isoformat() if valid_until is not None else None),
            },
        )

    assert response.status_code == 201

    body = response.json()

    assert isinstance(body, dict)

    return body


def calculate_quote_via_api(
    *,
    access_token: str,
    tenant_id: UUID,
    pricing_rule_id: UUID,
    shipment_id: UUID,
) -> Response:
    with TestClient(app) as client:
        return client.post(
            (
                f"/api/v1/tenants/{tenant_id}"
                f"/pricing-rules/{pricing_rule_id}"
                f"/shipments/{shipment_id}/quote"
            ),
            headers={
                "Authorization": f"Bearer {access_token}",
            },
        )


@pytest.mark.integration
async def test_calculate_rate_quote_endpoint_creates_persisted_quote() -> None:
    unique = uuid4()

    email = f"pricing-calculate-{unique}@example.com"
    password = "very-secure-pricing-password"
    tenant_slug = f"pricing-calculate-tenant-{unique}"
    role_name = f"pricing-calculate-role-{unique}"

    (
        tenant,
        customer,
        origin,
        destination,
    ) = await create_pricing_quote_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_rate_create_permission=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        shipment = create_shipment_via_api(
            access_token=access_token,
            tenant_id=tenant.id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
            weight="10.000",
        )

        pricing_rule = create_pricing_rule_via_api(
            access_token=access_token,
            tenant_id=tenant.id,
        )

        shipment_id = UUID(str(shipment["id"]))
        pricing_rule_id = UUID(str(pricing_rule["id"]))

        response = calculate_quote_via_api(
            access_token=access_token,
            tenant_id=tenant.id,
            pricing_rule_id=pricing_rule_id,
            shipment_id=shipment_id,
        )

        assert response.status_code == 201

        body = response.json()

        assert body["tenant_id"] == str(tenant.id)
        assert body["shipment_id"] == str(shipment_id)

        assert body["currency"] == "USD"

        assert body["base_amount"] == "25.00"
        assert body["surcharge_amount"] == "30.00"
        assert body["total_amount"] == "55.00"

        assert body["status"] == "draft"
        assert body["expires_at"] is None
        assert body["id"]

        rate_quote_id = UUID(body["id"])

        persisted = await get_rate_quote_from_database(
            rate_quote_id=rate_quote_id,
        )

        assert persisted is not None

        assert persisted.tenant_id == tenant.id
        assert persisted.shipment_id == shipment_id

        assert persisted.currency == "USD"

        assert persisted.base_amount == Decimal("25.00")
        assert persisted.surcharge_amount == Decimal("30.00")
        assert persisted.total_amount == Decimal("55.00")

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_calculate_rate_quote_endpoint_requires_rate_create_permission() -> None:
    unique = uuid4()

    email = f"pricing-calculate-denied-{unique}@example.com"
    password = "very-secure-pricing-password"
    tenant_slug = f"pricing-calculate-denied-tenant-{unique}"
    role_name = f"pricing-calculate-denied-role-{unique}"

    (
        tenant,
        customer,
        origin,
        destination,
    ) = await create_pricing_quote_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_rate_create_permission=False,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        shipment = create_shipment_via_api(
            access_token=access_token,
            tenant_id=tenant.id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
        )

        pricing_rule = create_pricing_rule_via_api(
            access_token=access_token,
            tenant_id=tenant.id,
        )

        response = calculate_quote_via_api(
            access_token=access_token,
            tenant_id=tenant.id,
            pricing_rule_id=UUID(str(pricing_rule["id"])),
            shipment_id=UUID(str(shipment["id"])),
        )

        assert response.status_code == 403
        assert response.json() == {
            "detail": "Permission denied",
        }

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_calculate_rate_quote_endpoint_rejects_unknown_shipment() -> None:
    unique = uuid4()

    email = f"pricing-missing-shipment-{unique}@example.com"
    password = "very-secure-pricing-password"
    tenant_slug = f"pricing-missing-shipment-tenant-{unique}"
    role_name = f"pricing-missing-shipment-role-{unique}"

    (
        tenant,
        _,
        _,
        _,
    ) = await create_pricing_quote_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_rate_create_permission=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        pricing_rule = create_pricing_rule_via_api(
            access_token=access_token,
            tenant_id=tenant.id,
        )

        response = calculate_quote_via_api(
            access_token=access_token,
            tenant_id=tenant.id,
            pricing_rule_id=UUID(str(pricing_rule["id"])),
            shipment_id=uuid4(),
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Shipment not found",
        }

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_calculate_rate_quote_endpoint_rejects_unknown_pricing_rule() -> None:
    unique = uuid4()

    email = f"pricing-missing-rule-{unique}@example.com"
    password = "very-secure-pricing-password"
    tenant_slug = f"pricing-missing-rule-tenant-{unique}"
    role_name = f"pricing-missing-rule-role-{unique}"

    (
        tenant,
        customer,
        origin,
        destination,
    ) = await create_pricing_quote_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_rate_create_permission=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        shipment = create_shipment_via_api(
            access_token=access_token,
            tenant_id=tenant.id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
        )

        response = calculate_quote_via_api(
            access_token=access_token,
            tenant_id=tenant.id,
            pricing_rule_id=uuid4(),
            shipment_id=UUID(str(shipment["id"])),
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Pricing rule not found",
        }

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_calculate_rate_quote_endpoint_rejects_inactive_pricing_rule() -> None:
    unique = uuid4()

    email = f"pricing-inactive-{unique}@example.com"
    password = "very-secure-pricing-password"
    tenant_slug = f"pricing-inactive-tenant-{unique}"
    role_name = f"pricing-inactive-role-{unique}"

    (
        tenant,
        customer,
        origin,
        destination,
    ) = await create_pricing_quote_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_rate_create_permission=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        shipment = create_shipment_via_api(
            access_token=access_token,
            tenant_id=tenant.id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
        )

        pricing_rule = create_pricing_rule_via_api(
            access_token=access_token,
            tenant_id=tenant.id,
        )

        pricing_rule_id = UUID(str(pricing_rule["id"]))

        await deactivate_pricing_rule(
            pricing_rule_id=pricing_rule_id,
        )

        response = calculate_quote_via_api(
            access_token=access_token,
            tenant_id=tenant.id,
            pricing_rule_id=pricing_rule_id,
            shipment_id=UUID(str(shipment["id"])),
        )

        assert response.status_code == 409
        assert response.json() == {
            "detail": "Pricing rule is inactive",
        }

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_calculate_rate_quote_endpoint_rejects_service_type_mismatch() -> None:
    unique = uuid4()

    email = f"pricing-service-mismatch-{unique}@example.com"
    password = "very-secure-pricing-password"
    tenant_slug = f"pricing-service-mismatch-tenant-{unique}"
    role_name = f"pricing-service-mismatch-role-{unique}"

    (
        tenant,
        customer,
        origin,
        destination,
    ) = await create_pricing_quote_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_rate_create_permission=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        shipment = create_shipment_via_api(
            access_token=access_token,
            tenant_id=tenant.id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
            service_type="express",
        )

        pricing_rule = create_pricing_rule_via_api(
            access_token=access_token,
            tenant_id=tenant.id,
            service_type="standard",
        )

        response = calculate_quote_via_api(
            access_token=access_token,
            tenant_id=tenant.id,
            pricing_rule_id=UUID(str(pricing_rule["id"])),
            shipment_id=UUID(str(shipment["id"])),
        )

        assert response.status_code == 409
        assert response.json() == {
            "detail": "Pricing rule does not match shipment service type",
        }

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_calculate_rate_quote_endpoint_rejects_future_pricing_rule() -> None:
    unique = uuid4()

    email = f"pricing-future-{unique}@example.com"
    password = "very-secure-pricing-password"
    tenant_slug = f"pricing-future-tenant-{unique}"
    role_name = f"pricing-future-role-{unique}"

    (
        tenant,
        customer,
        origin,
        destination,
    ) = await create_pricing_quote_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_rate_create_permission=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        shipment = create_shipment_via_api(
            access_token=access_token,
            tenant_id=tenant.id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
        )

        now = datetime.now(UTC)

        pricing_rule = create_pricing_rule_via_api(
            access_token=access_token,
            tenant_id=tenant.id,
            valid_from=now + timedelta(days=1),
            valid_until=now + timedelta(days=2),
        )

        response = calculate_quote_via_api(
            access_token=access_token,
            tenant_id=tenant.id,
            pricing_rule_id=UUID(str(pricing_rule["id"])),
            shipment_id=UUID(str(shipment["id"])),
        )

        assert response.status_code == 409
        assert response.json() == {
            "detail": "Pricing rule is not currently effective",
        }

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_calculate_rate_quote_endpoint_enforces_pricing_rule_tenant_isolation() -> None:
    unique = uuid4()

    email = f"pricing-isolation-{unique}@example.com"
    password = "very-secure-pricing-password"

    tenant_slug = f"pricing-isolation-tenant-{unique}"
    foreign_tenant_slug = f"pricing-isolation-foreign-{unique}"

    role_name = f"pricing-isolation-role-{unique}"

    (
        tenant,
        customer,
        origin,
        destination,
    ) = await create_pricing_quote_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_rate_create_permission=True,
    )

    _, foreign_pricing_rule = await create_foreign_pricing_rule(
        tenant_slug=foreign_tenant_slug,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        shipment = create_shipment_via_api(
            access_token=access_token,
            tenant_id=tenant.id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
        )

        response = calculate_quote_via_api(
            access_token=access_token,
            tenant_id=tenant.id,
            pricing_rule_id=foreign_pricing_rule.id,
            shipment_id=UUID(str(shipment["id"])),
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Pricing rule not found",
        }

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(
                tenant_slug,
                foreign_tenant_slug,
            ),
            role_name=role_name,
        )
