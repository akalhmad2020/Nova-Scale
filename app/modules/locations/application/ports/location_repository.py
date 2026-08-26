from typing import Protocol
from uuid import UUID

from app.modules.locations.infrastructure.models.location import Location


class LocationRepository(Protocol):
    async def get_by_id(
        self,
        location_id: UUID,
    ) -> Location | None: ...

    async def get_by_id_and_tenant(
        self,
        location_id: UUID,
        tenant_id: UUID,
    ) -> Location | None: ...

    async def get_by_code_and_tenant(
        self,
        code: str,
        tenant_id: UUID,
    ) -> Location | None: ...

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[Location]: ...

    def add(
        self,
        location: Location,
    ) -> None: ...
