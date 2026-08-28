from typing import Protocol
from uuid import UUID

from app.modules.carriers.infrastructure.models.carrier import Carrier


class CarrierRepository(Protocol):
    async def get_by_id_and_tenant(
        self,
        carrier_id: UUID,
        tenant_id: UUID,
    ) -> Carrier | None: ...

    async def get_by_code_and_tenant(
        self,
        code: str,
        tenant_id: UUID,
    ) -> Carrier | None: ...

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[Carrier]: ...

    def add(
        self,
        carrier: Carrier,
    ) -> None: ...
