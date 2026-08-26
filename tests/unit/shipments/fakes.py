from types import TracebackType
from uuid import UUID

from app.modules.customers.infrastructure.models.customer import Customer
from app.modules.locations.infrastructure.models.location import Location
from app.modules.shipments.infrastructure.models.shipment import Shipment


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


class FakeCustomerRepository:
    def __init__(self) -> None:
        self.items: list[Customer] = []

    async def get_by_id(
        self,
        customer_id: UUID,
    ) -> Customer | None:
        return next(
            (
                customer
                for customer in self.items
                if customer.id == customer_id and customer.deleted_at is None
            ),
            None,
        )

    async def get_by_id_and_tenant(
        self,
        customer_id: UUID,
        tenant_id: UUID,
    ) -> Customer | None:
        return next(
            (
                customer
                for customer in self.items
                if customer.id == customer_id
                and customer.tenant_id == tenant_id
                and customer.deleted_at is None
            ),
            None,
        )

    async def get_by_code_and_tenant(
        self,
        code: str,
        tenant_id: UUID,
    ) -> Customer | None:
        return next(
            (
                customer
                for customer in self.items
                if customer.code == code
                and customer.tenant_id == tenant_id
                and customer.deleted_at is None
            ),
            None,
        )

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[Customer]:
        return [
            customer
            for customer in self.items
            if customer.tenant_id == tenant_id and customer.deleted_at is None
        ]

    def add(
        self,
        customer: Customer,
    ) -> None:
        self.items.append(customer)


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
        self.shipments = FakeShipmentRepository()
        self.customers = FakeCustomerRepository()
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
        shipment: Shipment,
    ) -> None:
        self.refreshed = True
