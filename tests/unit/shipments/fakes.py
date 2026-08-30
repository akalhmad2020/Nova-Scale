from collections.abc import Sequence
from datetime import datetime
from types import TracebackType
from uuid import UUID, uuid4

from app.modules.audit.infrastructure.models.audit_log import AuditLog
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


class FakeAuditLogRepository:
    def __init__(self) -> None:
        self.items: list[AuditLog] = []

    async def add(
        self,
        audit_log: AuditLog,
    ) -> None:
        self.items.append(audit_log)

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        audit_log_id: UUID,
    ) -> AuditLog | None:
        return next(
            (
                audit_log
                for audit_log in self.items
                if audit_log.tenant_id == tenant_id and audit_log.id == audit_log_id
            ),
            None,
        )

    async def list_for_tenant(
        self,
        *,
        tenant_id: UUID,
        limit: int = 100,
        offset: int = 0,
        actor_id: UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> Sequence[AuditLog]:
        items = [audit_log for audit_log in self.items if audit_log.tenant_id == tenant_id]

        if actor_id is not None:
            items = [audit_log for audit_log in items if audit_log.actor_id == actor_id]

        if action is not None:
            items = [audit_log for audit_log in items if audit_log.action == action]

        if resource_type is not None:
            items = [audit_log for audit_log in items if audit_log.resource_type == resource_type]

        if resource_id is not None:
            items = [audit_log for audit_log in items if audit_log.resource_id == resource_id]

        if occurred_from is not None:
            items = [audit_log for audit_log in items if audit_log.occurred_at >= occurred_from]

        if occurred_to is not None:
            items = [audit_log for audit_log in items if audit_log.occurred_at <= occurred_to]

        return items[offset : offset + limit]


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.shipments = FakeShipmentRepository()
        self.customers = FakeCustomerRepository()
        self.locations = FakeLocationRepository()
        self.audit_logs = FakeAuditLogRepository()

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

        for shipment in self.shipments.items:
            if getattr(shipment, "id", None) is None:
                shipment.id = uuid4()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def refresh(
        self,
        shipment: Shipment,
    ) -> None:
        self.refreshed = True
