from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.modules.payments.infrastructure.models.payment_allocation import (
    PaymentAllocation,
)


class PaymentAllocationRepository(Protocol):
    async def add(
        self,
        payment_allocation: PaymentAllocation,
    ) -> None: ...

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        payment_allocation_id: UUID,
    ) -> PaymentAllocation | None: ...

    async def get_by_payment_and_invoice(
        self,
        *,
        tenant_id: UUID,
        payment_id: UUID,
        invoice_id: UUID,
    ) -> PaymentAllocation | None: ...

    async def list_by_payment(
        self,
        *,
        tenant_id: UUID,
        payment_id: UUID,
    ) -> list[PaymentAllocation]: ...

    async def list_by_invoice(
        self,
        *,
        tenant_id: UUID,
        invoice_id: UUID,
    ) -> list[PaymentAllocation]: ...

    async def sum_posted_by_invoice(
        self,
        *,
        tenant_id: UUID,
        invoice_id: UUID,
    ) -> Decimal: ...

    async def delete(
        self,
        payment_allocation: PaymentAllocation,
    ) -> None: ...
