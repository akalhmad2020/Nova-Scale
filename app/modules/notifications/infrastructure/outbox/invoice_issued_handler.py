from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.modules.notifications.application.contracts import (
    NotificationIntent,
)
from app.modules.notifications.domain.enums import NotificationChannel
from app.shared.outbox.infrastructure.models.outbox_message import (
    OutboxMessage,
)


class InvoiceIssuedCustomerNotFoundError(Exception):
    pass


class InvoiceIssuedCustomerHasNoEmailError(Exception):
    pass


class InvalidInvoiceIssuedOutboxPayloadError(Exception):
    pass


@dataclass(frozen=True)
class InvoiceIssuedCustomer:
    id: UUID
    email: str | None


class InvoiceIssuedCustomerResolver(Protocol):
    async def get_customer(
        self,
        *,
        tenant_id: UUID,
        customer_id: UUID,
    ) -> InvoiceIssuedCustomer | None: ...


class CreateNotificationFromIntent(Protocol):
    async def execute(
        self,
        *,
        tenant_id: UUID,
        intent: NotificationIntent,
    ) -> object: ...


class InvoiceIssuedOutboxHandler:
    def __init__(
        self,
        *,
        customer_resolver: InvoiceIssuedCustomerResolver,
        create_notification: CreateNotificationFromIntent,
    ) -> None:
        self._customer_resolver = customer_resolver
        self._create_notification = create_notification

    async def handle(
        self,
        message: OutboxMessage,
    ) -> None:
        payload = message.payload

        invoice_id = self._require_uuid(
            payload=payload,
            field="invoice_id",
        )
        customer_id = self._require_uuid(
            payload=payload,
            field="customer_id",
        )
        invoice_number = self._require_string(
            payload=payload,
            field="invoice_number",
        )
        currency = self._require_string(
            payload=payload,
            field="currency",
        )
        total_amount = self._require_string(
            payload=payload,
            field="total_amount",
        )

        customer = await self._customer_resolver.get_customer(
            tenant_id=message.tenant_id,
            customer_id=customer_id,
        )

        if customer is None:
            raise InvoiceIssuedCustomerNotFoundError("Invoice customer was not found.")

        if customer.email is None:
            raise InvoiceIssuedCustomerHasNoEmailError(
                "Invoice customer does not have an email address."
            )

        recipient = customer.email.strip()

        if not recipient:
            raise InvoiceIssuedCustomerHasNoEmailError(
                "Invoice customer does not have an email address."
            )

        intent = NotificationIntent(
            event_type=message.event_type,
            recipient=recipient,
            channel=NotificationChannel.EMAIL,
            subject=f"Invoice {invoice_number} issued",
            body=(f"Invoice {invoice_number} has been issued. Total: {total_amount} {currency}."),
            idempotency_key=f"invoice-issued:{invoice_id}",
            scheduled_at=None,
        )

        await self._create_notification.execute(
            tenant_id=message.tenant_id,
            intent=intent,
        )

    def _require_string(
        self,
        *,
        payload: dict[str, object],
        field: str,
    ) -> str:
        value = payload.get(field)

        if not isinstance(value, str):
            raise InvalidInvoiceIssuedOutboxPayloadError(
                f"Invoice issued outbox payload field '{field}' must be a string."
            )

        normalized = value.strip()

        if not normalized:
            raise InvalidInvoiceIssuedOutboxPayloadError(
                f"Invoice issued outbox payload field '{field}' cannot be empty."
            )

        return normalized

    def _require_uuid(
        self,
        *,
        payload: dict[str, object],
        field: str,
    ) -> UUID:
        value = self._require_string(
            payload=payload,
            field=field,
        )

        try:
            return UUID(value)
        except ValueError as exc:
            raise InvalidInvoiceIssuedOutboxPayloadError(
                f"Invoice issued outbox payload field '{field}' must be a valid UUID."
            ) from exc
