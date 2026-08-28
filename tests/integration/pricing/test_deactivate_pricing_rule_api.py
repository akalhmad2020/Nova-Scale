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
from app.modules.identity.domain.enums import MembershipStatus, TenantStatus
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.auth_session import AuthSession
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.permission import Permission
from app.modules.identity.infrastructure.models.role import Role
from app.modules.identity.infrastructure.models.role_permission import RolePermission
from app.modules.identity.infrastructure.models.tenant import Tenant
from app.modules.identity.infrastructure.models.user import User
from app.modules.identity.infrastructure.security.password_hasher import (
    Argon2PasswordHasher,
)
from app.modules.pricing.domain.enums import PricingRuleStatus
from app.modules.pricing.infrastructure.models import PricingRule
from app.modules.shipments.domain.enums import ServiceType


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
                    delete(PricingRule).where(PricingRule.tenant_id.in_(tenant_ids))
                )

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


async def create_deactivate_context(
    *,
    email: str,
    password: str,
    tenant_slug: str,
    role_name: str,
    assign_permission: bool,
) -> Tenant:
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
                last_name="Deactivator",
                is_active=True,
            )

            tenant = Tenant(
                name="Pricing Deactivate Integration Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Pricing deactivate integration role",
            )

            permission = await session.scalar(
                select(Permission).where(Permission.code == Permissions.PRICING_RULE_DELETE)
            )

            if permission is None:
                permission = Permission(
                    code=Permissions.PRICING_RULE_DELETE,
                    description="Deactivate pricing rules",
                )
                session.add(permission)

            session.add_all([user, tenant, role])

            await session.flush()

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

            return tenant

    finally:
        await engine.dispose()


async def create_pricing_rule(
    *,
    tenant_id: UUID,
    status: PricingRuleStatus = PricingRuleStatus.ACTIVE,
) -> PricingRule:
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
            pricing_rule = PricingRule(
                tenant_id=tenant_id,
                name="Deactivate Rule",
                service_type=ServiceType.STANDARD,
                currency="USD",
                base_amount=Decimal("25.00"),
                price_per_kg=Decimal("2.5000"),
                surcharge_amount=Decimal("5.00"),
                status=status,
                valid_from=None,
                valid_until=None,
            )

            session.add(pricing_rule)
            await session.commit()

            return pricing_rule

    finally:
        await engine.dispose()


async def create_foreign_rule(
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
                name="Foreign Pricing Deactivate Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            session.add(tenant)
            await session.flush()

            pricing_rule = PricingRule(
                tenant_id=tenant.id,
                name="Foreign Deactivate Rule",
                service_type=ServiceType.STANDARD,
                currency="USD",
                base_amount=Decimal("30.00"),
                price_per_kg=Decimal("3.0000"),
                surcharge_amount=Decimal("6.00"),
                status=PricingRuleStatus.ACTIVE,
                valid_from=None,
                valid_until=None,
            )

            session.add(pricing_rule)
            await session.commit()

            return tenant, pricing_rule

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
async def test_deactivate_pricing_rule_endpoint_deactivates_rule() -> None:
    unique = uuid4()

    email = f"pricing-deactivate-{unique}@example.com"
    password = "very-secure-pricing-password"
    tenant_slug = f"pricing-deactivate-tenant-{unique}"
    role_name = f"pricing-deactivate-role-{unique}"

    tenant = await create_deactivate_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        pricing_rule = await create_pricing_rule(
            tenant_id=tenant.id,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                (f"/api/v1/tenants/{tenant.id}/pricing-rules/{pricing_rule.id}/deactivate"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(pricing_rule.id)
        assert body["tenant_id"] == str(tenant.id)
        assert body["status"] == "inactive"

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_deactivate_pricing_rule_endpoint_rejects_already_inactive_rule() -> None:
    unique = uuid4()

    email = f"pricing-deactivate-inactive-{unique}@example.com"
    password = "very-secure-pricing-password"
    tenant_slug = f"pricing-deactivate-inactive-tenant-{unique}"
    role_name = f"pricing-deactivate-inactive-role-{unique}"

    tenant = await create_deactivate_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        pricing_rule = await create_pricing_rule(
            tenant_id=tenant.id,
            status=PricingRuleStatus.INACTIVE,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                (f"/api/v1/tenants/{tenant.id}/pricing-rules/{pricing_rule.id}/deactivate"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 409

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_deactivate_pricing_rule_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"pricing-deactivate-denied-{unique}@example.com"
    password = "very-secure-pricing-password"
    tenant_slug = f"pricing-deactivate-denied-tenant-{unique}"
    role_name = f"pricing-deactivate-denied-role-{unique}"

    tenant = await create_deactivate_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=False,
    )

    try:
        pricing_rule = await create_pricing_rule(
            tenant_id=tenant.id,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                (f"/api/v1/tenants/{tenant.id}/pricing-rules/{pricing_rule.id}/deactivate"),
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
async def test_deactivate_pricing_rule_endpoint_rejects_unknown_rule() -> None:
    unique = uuid4()

    email = f"pricing-deactivate-missing-{unique}@example.com"
    password = "very-secure-pricing-password"
    tenant_slug = f"pricing-deactivate-missing-tenant-{unique}"
    role_name = f"pricing-deactivate-missing-role-{unique}"

    tenant = await create_deactivate_context(
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
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/pricing-rules/{uuid4()}/deactivate",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 404
        assert response.json() == {"detail": "Pricing rule not found"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_deactivate_pricing_rule_endpoint_rejects_foreign_rule() -> None:
    unique = uuid4()

    email = f"pricing-deactivate-foreign-{unique}@example.com"
    password = "very-secure-pricing-password"

    tenant_slug = f"pricing-deactivate-tenant-{unique}"
    foreign_slug = f"pricing-deactivate-foreign-tenant-{unique}"
    role_name = f"pricing-deactivate-foreign-role-{unique}"

    tenant = await create_deactivate_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    _, foreign_rule = await create_foreign_rule(
        tenant_slug=foreign_slug,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                (f"/api/v1/tenants/{tenant.id}/pricing-rules/{foreign_rule.id}/deactivate"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 404
        assert response.json() == {"detail": "Pricing rule not found"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(
                tenant_slug,
                foreign_slug,
            ),
            role_name=role_name,
        )
