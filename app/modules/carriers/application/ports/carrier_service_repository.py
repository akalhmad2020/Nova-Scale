from typing import Protocol
from uuid import UUID

from app.modules.carriers.infrastructure.models.carrier_service import (
    CarrierService,
)


class CarrierServiceRepository(Protocol):
    async def get_by_id_and_tenant(
        self,
        carrier_service_id: UUID,
        tenant_id: UUID,
    ) -> CarrierService | None: ...

    async def get_by_code_and_carrier(
        self,
        *,
        tenant_id: UUID,
        carrier_id: UUID,
        code: str,
    ) -> CarrierService | None: ...

    async def list_by_carrier(
        self,
        *,
        tenant_id: UUID,
        carrier_id: UUID,
    ) -> list[CarrierService]: ...

    def add(
        self,
        carrier_service: CarrierService,
    ) -> None: ...
