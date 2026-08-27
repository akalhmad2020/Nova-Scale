from types import TracebackType
from uuid import UUID

from app.modules.locations.infrastructure.models.location import Location
from app.modules.shipment_events.infrastructure.models.shipment_event import (
    ShipmentEvent,
)
from app.modules.shipments.infrastructure.models.shipment import Shipment


class FakeShipmentEventRepository:
    def __init__(self) -> None:
        self.items: list[ShipmentEvent] = []

    async def list_by_shipment(
        self,
        shipment_id: UUID,
        tenant_id: UUID,
    ) -> list[ShipmentEvent]:
        return sorted(
            [
                event
                for event in self.items
                if event.shipment_id == shipment_id and event.tenant_id == tenant_id
            ],
            key=lambda event: (
                event.occurred_at,
                event.created_at,
            ),
        )

    def add(
        self,
        event: ShipmentEvent,
    ) -> None:
        self.items.append(event)


class FakeShipmentRepository:
    def __init__(self) -> None:
        self.items: list[Shipment] = []

    async def get_by_id_and_tenant(
        self,
        shipment_id: UUID,
        tenant_id: UUID,
    ) -> Shipment | None:
        return next(
            (
                shipment
                for shipment in self.items
                if shipment.id == shipment_id
                and shipment.tenant_id == tenant_id
                and shipment.deleted_at is None
            ),
            None,
        )

    async def get_by_tracking_number_and_tenant(
        self,
        tracking_number: str,
        tenant_id: UUID,
    ) -> Shipment | None:
        return next(
            (
                shipment
                for shipment in self.items
                if shipment.tracking_number == tracking_number
                and shipment.tenant_id == tenant_id
                and shipment.deleted_at is None
            ),
            None,
        )

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[Shipment]:
        return [
            shipment
            for shipment in self.items
            if shipment.tenant_id == tenant_id and shipment.deleted_at is None
        ]

    def add(
        self,
        shipment: Shipment,
    ) -> None:
        self.items.append(shipment)


class FakeLocationRepository:
    def __init__(self) -> None:
        self.items: list[Location] = []

    async def get_by_id(
        self,
        location_id: UUID,
    ) -> Location | None:
        return next(
            (
                location
                for location in self.items
                if location.id == location_id and location.deleted_at is None
            ),
            None,
        )

    async def get_by_id_and_tenant(
        self,
        location_id: UUID,
        tenant_id: UUID,
    ) -> Location | None:
        return next(
            (
                location
                for location in self.items
                if location.id == location_id
                and location.tenant_id == tenant_id
                and location.deleted_at is None
            ),
            None,
        )

    async def get_by_code_and_tenant(
        self,
        code: str,
        tenant_id: UUID,
    ) -> Location | None:
        return next(
            (
                location
                for location in self.items
                if location.code == code
                and location.tenant_id == tenant_id
                and location.deleted_at is None
            ),
            None,
        )

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[Location]:
        return [
            location
            for location in self.items
            if location.tenant_id == tenant_id and location.deleted_at is None
        ]

    def add(
        self,
        location: Location,
    ) -> None:
        self.items.append(location)


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.shipment_events = FakeShipmentEventRepository()
        self.shipments = FakeShipmentRepository()
        self.locations = FakeLocationRepository()

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
        event: ShipmentEvent,
    ) -> None:
        self.refreshed = True
