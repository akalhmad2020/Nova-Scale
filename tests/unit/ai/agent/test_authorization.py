from uuid import UUID, uuid4

import pytest

from app.ai.application.agent.authorization import (
    AgentAuthorizationContext,
    AgentAuthorizationService,
)
from app.modules.identity.domain.permissions import Permissions


class FakePermissionChecker:
    def __init__(
        self,
        *,
        allowed_permissions: set[str],
    ) -> None:
        self.allowed_permissions = allowed_permissions
        self.calls: list[
            tuple[
                UUID,
                str,
            ]
        ] = []

    async def __call__(
        self,
        role_id: UUID,
        permission_code: str,
    ) -> bool:
        self.calls.append(
            (
                role_id,
                permission_code,
            )
        )

        return permission_code in self.allowed_permissions


@pytest.mark.asyncio
async def test_direct_answer_requires_no_permission() -> None:
    checker = FakePermissionChecker(
        allowed_permissions=set(),
    )

    service = AgentAuthorizationService(
        permission_checker=checker,
    )

    allowed = await service.is_allowed(
        context=AgentAuthorizationContext(
            role_id=uuid4(),
        ),
        route="direct_answer",
    )

    assert allowed is True
    assert checker.calls == []


@pytest.mark.asyncio
async def test_get_shipment_requires_shipment_read() -> None:
    role_id = uuid4()

    checker = FakePermissionChecker(
        allowed_permissions={
            Permissions.SHIPMENT_READ,
        },
    )

    service = AgentAuthorizationService(
        permission_checker=checker,
    )

    allowed = await service.is_allowed(
        context=AgentAuthorizationContext(
            role_id=role_id,
        ),
        route="get_shipment",
    )

    assert allowed is True

    assert checker.calls == [
        (
            role_id,
            Permissions.SHIPMENT_READ,
        )
    ]


@pytest.mark.asyncio
async def test_get_shipments_requires_shipment_read() -> None:
    role_id = uuid4()

    checker = FakePermissionChecker(
        allowed_permissions={
            Permissions.SHIPMENT_READ,
        },
    )

    service = AgentAuthorizationService(
        permission_checker=checker,
    )

    allowed = await service.is_allowed(
        context=AgentAuthorizationContext(
            role_id=role_id,
        ),
        route="get_shipments",
    )

    assert allowed is True

    assert checker.calls == [
        (
            role_id,
            Permissions.SHIPMENT_READ,
        )
    ]


@pytest.mark.asyncio
async def test_get_shipments_is_denied_without_shipment_read() -> None:
    role_id = uuid4()

    checker = FakePermissionChecker(
        allowed_permissions=set(),
    )

    service = AgentAuthorizationService(
        permission_checker=checker,
    )

    allowed = await service.is_allowed(
        context=AgentAuthorizationContext(
            role_id=role_id,
        ),
        route="get_shipments",
    )

    assert allowed is False

    assert checker.calls == [
        (
            role_id,
            Permissions.SHIPMENT_READ,
        )
    ]


@pytest.mark.asyncio
async def test_summary_requires_shipment_and_event_read() -> None:
    role_id = uuid4()

    checker = FakePermissionChecker(
        allowed_permissions={
            Permissions.SHIPMENT_READ,
            Permissions.SHIPMENT_EVENT_READ,
        },
    )

    service = AgentAuthorizationService(
        permission_checker=checker,
    )

    allowed = await service.is_allowed(
        context=AgentAuthorizationContext(
            role_id=role_id,
        ),
        route="summarize_shipment",
    )

    assert allowed is True

    assert checker.calls == [
        (
            role_id,
            Permissions.SHIPMENT_READ,
        ),
        (
            role_id,
            Permissions.SHIPMENT_EVENT_READ,
        ),
    ]


@pytest.mark.asyncio
async def test_summary_is_denied_without_event_read() -> None:
    role_id = uuid4()

    checker = FakePermissionChecker(
        allowed_permissions={
            Permissions.SHIPMENT_READ,
        },
    )

    service = AgentAuthorizationService(
        permission_checker=checker,
    )

    allowed = await service.is_allowed(
        context=AgentAuthorizationContext(
            role_id=role_id,
        ),
        route="summarize_shipment",
    )

    assert allowed is False

    assert checker.calls == [
        (
            role_id,
            Permissions.SHIPMENT_READ,
        ),
        (
            role_id,
            Permissions.SHIPMENT_EVENT_READ,
        ),
    ]


@pytest.mark.asyncio
async def test_operational_analysis_requires_timeline_access() -> None:
    role_id = uuid4()

    checker = FakePermissionChecker(
        allowed_permissions={
            Permissions.SHIPMENT_READ,
            Permissions.SHIPMENT_EVENT_READ,
        },
    )

    service = AgentAuthorizationService(
        permission_checker=checker,
    )

    allowed = await service.is_allowed(
        context=AgentAuthorizationContext(
            role_id=role_id,
        ),
        route="analyze_shipment_operations",
    )

    assert allowed is True

    assert checker.calls == [
        (
            role_id,
            Permissions.SHIPMENT_READ,
        ),
        (
            role_id,
            Permissions.SHIPMENT_EVENT_READ,
        ),
    ]


@pytest.mark.asyncio
async def test_retrieve_context_requires_document_read() -> None:
    role_id = uuid4()

    checker = FakePermissionChecker(
        allowed_permissions={
            Permissions.DOCUMENT_READ,
        },
    )

    service = AgentAuthorizationService(
        permission_checker=checker,
    )

    allowed = await service.is_allowed(
        context=AgentAuthorizationContext(
            role_id=role_id,
        ),
        route="retrieve_context",
    )

    assert allowed is True

    assert checker.calls == [
        (
            role_id,
            Permissions.DOCUMENT_READ,
        )
    ]
