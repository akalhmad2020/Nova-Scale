from uuid import UUID, uuid4

import pytest

from app.ai.application.agent.authorization import (
    AgentAuthorizationContext,
    AgentAuthorizationService,
)
from app.modules.identity.domain.permissions import Permissions


@pytest.mark.asyncio
async def test_transition_action_requires_read_and_transition_permissions() -> None:
    role_id = uuid4()
    checks: list[str] = []

    async def checker(_role_id: UUID, permission_code: str) -> bool:
        assert _role_id == role_id
        checks.append(permission_code)
        return True

    service = AgentAuthorizationService(permission_checker=checker)

    allowed = await service.is_allowed(
        context=AgentAuthorizationContext(role_id=role_id),
        route="transition_shipment_status",
    )

    assert allowed is True
    assert checks == [
        Permissions.SHIPMENT_READ,
        Permissions.SHIPMENT_TRANSITION,
    ]


@pytest.mark.asyncio
async def test_notes_action_requires_read_and_update_permissions() -> None:
    role_id = uuid4()
    checks: list[str] = []

    async def checker(_role_id: UUID, permission_code: str) -> bool:
        assert _role_id == role_id
        checks.append(permission_code)
        return True

    service = AgentAuthorizationService(permission_checker=checker)

    allowed = await service.is_allowed(
        context=AgentAuthorizationContext(role_id=role_id),
        route="update_shipment_notes",
    )

    assert allowed is True
    assert checks == [
        Permissions.SHIPMENT_READ,
        Permissions.SHIPMENT_UPDATE,
    ]
