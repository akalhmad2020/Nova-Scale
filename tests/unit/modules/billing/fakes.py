from collections.abc import Sequence
from types import TracebackType
from typing import cast
from uuid import UUID, uuid4

from app.modules.billing.application.ports.invoice_line_repository import (
    InvoiceLineRepository,
)
from app.modules.billing.application.ports.invoice_repository import (
    InvoiceRepository,
)
from app.modules.billing.infrastructure.models.invoice import Invoice
from app.modules.billing.infrastructure.models.invoice_line import InvoiceLine
from app.modules.customers.infrastructure.models.customer import Customer
from app.modules.customers.infrastructure.repositories.customer_repository import (
    CustomerRepository,
)
from app.modules.shipments.infrastructure.models.shipment import Shipment
from app.modules.shipments.infrastructure.repositories.shipment_repository import (
    ShipmentRepository,
)


class FakeInvoiceRepository:
    def __init__(self) -> None:
        self.items: list[Invoice] = []

    async def add(
        self,
        invoice: Invoice,
    ) -> None:
        invoice.id = uuid4()
        self.items.append(invoice)

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        invoice_id: UUID,
    ) -> Invoice | None:
        for invoice in self.items:
            if invoice.tenant_id == tenant_id and invoice.id == invoice_id:
                return invoice

        return None

    async def get_by_number(
        self,
        *,
        tenant_id: UUID,
        invoice_number: str,
    ) -> Invoice | None:
        for invoice in self.items:
            if invoice.tenant_id == tenant_id and invoice.invoice_number == invoice_number:
                return invoice

        return None

    async def list_by_tenant(
        self,
        *,
        tenant_id: UUID,
    ) -> Sequence[Invoice]:
        return [invoice for invoice in self.items if invoice.tenant_id == tenant_id]

    async def refresh(
        self,
        invoice: Invoice,
    ) -> None:
        return None


class FakeInvoiceLineRepository:
    def __init__(self) -> None:
        self.items: list[InvoiceLine] = []

    async def add(
        self,
        invoice_line: InvoiceLine,
    ) -> None:
        invoice_line.id = uuid4()
        self.items.append(invoice_line)

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        invoice_line_id: UUID,
    ) -> InvoiceLine | None:
        for invoice_line in self.items:
            if invoice_line.tenant_id == tenant_id and invoice_line.id == invoice_line_id:
                return invoice_line

        return None

    async def list_by_invoice(
        self,
        *,
        tenant_id: UUID,
        invoice_id: UUID,
    ) -> Sequence[InvoiceLine]:
        return [
            invoice_line
            for invoice_line in self.items
            if (invoice_line.tenant_id == tenant_id and invoice_line.invoice_id == invoice_id)
        ]

    async def delete(
        self,
        invoice_line: InvoiceLine,
    ) -> None:
        self.items.remove(invoice_line)


class FakeCustomerRepository:
    def __init__(self) -> None:
        self.items: list[Customer] = []

    def add_existing(
        self,
        *,
        customer_id: UUID,
        tenant_id: UUID,
    ) -> Customer:
        customer = Customer()
        customer.id = customer_id
        customer.tenant_id = tenant_id

        self.items.append(customer)

        return customer

    async def get_by_id_and_tenant(
        self,
        customer_id: UUID,
        tenant_id: UUID,
    ) -> Customer | None:
        for customer in self.items:
            if customer.id == customer_id and customer.tenant_id == tenant_id:
                return customer

        return None


class FakeShipmentRepository:
    def __init__(self) -> None:
        self.items: list[Shipment] = []

    def add_existing(
        self,
        *,
        shipment_id: UUID,
        tenant_id: UUID,
    ) -> Shipment:
        shipment = Shipment()
        shipment.id = shipment_id
        shipment.tenant_id = tenant_id

        self.items.append(shipment)

        return shipment

    async def get_by_id_and_tenant(
        self,
        shipment_id: UUID,
        tenant_id: UUID,
    ) -> Shipment | None:
        for shipment in self.items:
            if shipment.id == shipment_id and shipment.tenant_id == tenant_id:
                return shipment

        return None


class FakeBillingUnitOfWork:
    def __init__(self) -> None:
        self.fake_invoices = FakeInvoiceRepository()
        self.fake_invoice_lines = FakeInvoiceLineRepository()
        self.fake_customers = FakeCustomerRepository()
        self.fake_shipments = FakeShipmentRepository()

        self.invoices: InvoiceRepository = self.fake_invoices
        self.invoice_lines: InvoiceLineRepository = self.fake_invoice_lines

        self.customers: CustomerRepository = cast(
            CustomerRepository,
            self.fake_customers,
        )
        self.shipments: ShipmentRepository = cast(
            ShipmentRepository,
            self.fake_shipments,
        )

        self.committed = False
        self.rolled_back = False

    async def __aenter__(
        self,
    ) -> "FakeBillingUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True
