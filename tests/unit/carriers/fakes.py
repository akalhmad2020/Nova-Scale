from types import TracebackType
from uuid import UUID

from app.modules.carriers.infrastructure.models.carrier import Carrier
from app.modules.carriers.infrastructure.models.carrier_service import (
    CarrierService,
)


class FakeCarrierRepository:
    def __init__(self) -> None:
        self.items: list[Carrier] = []

    async def get_by_id_and_tenant(
        self,
        carrier_id: UUID,
        tenant_id: UUID,
    ) -> Carrier | None:
        return next(
            (
                carrier
                for carrier in self.items
                if carrier.id == carrier_id and carrier.tenant_id == tenant_id
            ),
            None,
        )

    async def get_by_code_and_tenant(
        self,
        code: str,
        tenant_id: UUID,
    ) -> Carrier | None:
        return next(
            (
                carrier
                for carrier in self.items
                if carrier.code == code and carrier.tenant_id == tenant_id
            ),
            None,
        )

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[Carrier]:
        return [carrier for carrier in self.items if carrier.tenant_id == tenant_id]

    def add(
        self,
        carrier: Carrier,
    ) -> None:
        self.items.append(carrier)


class FakeCarrierServiceRepository:
    def __init__(self) -> None:
        self.items: list[CarrierService] = []

    async def get_by_id_and_tenant(
        self,
        carrier_service_id: UUID,
        tenant_id: UUID,
    ) -> CarrierService | None:
        return next(
            (
                service
                for service in self.items
                if service.id == carrier_service_id and service.tenant_id == tenant_id
            ),
            None,
        )

    async def get_by_code_and_carrier(
        self,
        *,
        tenant_id: UUID,
        carrier_id: UUID,
        code: str,
    ) -> CarrierService | None:
        return next(
            (
                service
                for service in self.items
                if service.tenant_id == tenant_id
                and service.carrier_id == carrier_id
                and service.code == code
            ),
            None,
        )

    async def list_by_carrier(
        self,
        *,
        tenant_id: UUID,
        carrier_id: UUID,
    ) -> list[CarrierService]:
        return [
            service
            for service in self.items
            if service.tenant_id == tenant_id and service.carrier_id == carrier_id
        ]

    def add(
        self,
        carrier_service: CarrierService,
    ) -> None:
        self.items.append(carrier_service)


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.carriers = FakeCarrierRepository()
        self.carrier_services = FakeCarrierServiceRepository()

        self.flushed = False
        self.committed = False
        self.rolled_back = False
        self.refreshed = False

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def flush(self) -> None:
        self.flushed = True

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def refresh(
        self,
        model: Carrier | CarrierService,
    ) -> None:
        self.refreshed = True
