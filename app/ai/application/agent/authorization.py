from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

from app.ai.application.agent.decision import AgentRoute
from app.modules.identity.domain.permissions import Permissions

type PermissionChecker = Callable[
    [UUID, str],
    Awaitable[bool],
]


@dataclass(frozen=True, slots=True)
class AgentAuthorizationContext:
    role_id: UUID


class AgentAuthorizationService:
    def __init__(
        self,
        *,
        permission_checker: PermissionChecker,
    ) -> None:
        self._permission_checker = permission_checker

    async def is_allowed(
        self,
        *,
        context: AgentAuthorizationContext,
        route: AgentRoute,
    ) -> bool:
        required_permissions = self._required_permissions(route)

        for permission_code in required_permissions:
            allowed = await self._permission_checker(
                context.role_id,
                permission_code,
            )

            if not allowed:
                return False

        return True

    @staticmethod
    def _required_permissions(
        route: AgentRoute,
    ) -> tuple[str, ...]:
        permissions_by_route: dict[
            AgentRoute,
            tuple[str, ...],
        ] = {
            "direct_answer": (),
            "get_shipment": (Permissions.SHIPMENT_READ,),
            "get_shipments": (Permissions.SHIPMENT_READ,),
            "summarize_shipment": (
                Permissions.SHIPMENT_READ,
                Permissions.SHIPMENT_EVENT_READ,
            ),
            "analyze_shipment_operations": (
                Permissions.SHIPMENT_READ,
                Permissions.SHIPMENT_EVENT_READ,
            ),
            "retrieve_context": (Permissions.DOCUMENT_READ,),
            "transition_shipment_status": (
                Permissions.SHIPMENT_READ,
                Permissions.SHIPMENT_TRANSITION,
            ),
            "update_shipment_notes": (
                Permissions.SHIPMENT_READ,
                Permissions.SHIPMENT_UPDATE,
            ),
        }

        return permissions_by_route[route]
