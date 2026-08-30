from uuid import UUID, uuid4

import pytest

from app.modules.notifications.application.contracts import (
    NotificationIntent,
)
from app.modules.notifications.domain.enums import NotificationChannel
from app.modules.notifications.infrastructure.outbox.invoice_issued_handler import (
    InvalidInvoiceIssuedOutboxPayloadError,
    InvoiceIssuedCustomer,
    InvoiceIssuedCustomerHasNoEmailError,
    InvoiceIssuedCustomerNotFoundError,
    InvoiceIssuedOutboxHandler,
)
from app.shared.outbox.domain.enums import OutboxMessageStatus
from app.shared.outbox.infrastructure.models.outbox_message import (
    OutboxMessage,
)


class FakeInvoiceIssuedCustomerResolver:
    def __init__(
        self,
        customer: InvoiceIssuedCustomer | None,
    ) -> None:
        self.customer = customer
        self.calls: list[tuple[UUID, UUID]] = []

    async def get_customer(
        self,
        *,
        tenant_id: UUID,
        customer_id: UUID,
    ) -> InvoiceIssuedCustomer | None:
        self.calls.append(
            (
                tenant_id,
                customer_id,
            )
        )

        return self.customer


class FakeCreateNotificationFromIntentUseCase:
    def __init__(self) -> None:
        self.calls: list[tuple[UUID, NotificationIntent]] = []

    async def execute(
        self,
        *,
        tenant_id: UUID,
        intent: NotificationIntent,
    ) -> object:
        self.calls.append(
            (
                tenant_id,
                intent,
            )
        )

        return object()


def make_message(
    *,
    tenant_id: UUID,
    invoice_id: UUID,
    customer_id: UUID,
) -> OutboxMessage:
    return OutboxMessage(
        tenant_id=tenant_id,
        event_type="invoice.issued",
        payload={
            "invoice_id": str(invoice_id),
            "customer_id": str(customer_id),
            "invoice_number": "INV-1001",
            "currency": "USD",
            "subtotal": "100.00",
            "tax_amount": "10.00",
            "total_amount": "110.00",
            "issued_at": "2026-08-29T20:00:00+00:00",
        },
        status=OutboxMessageStatus.PENDING.value,
        attempt_count=0,
        available_at=None,
        processed_at=None,
        last_error=None,
        claim_token=None,
        lease_expires_at=None,
    )


async def test_invoice_issued_handler_creates_email_notification() -> None:
    tenant_id = uuid4()
    invoice_id = uuid4()
    customer_id = uuid4()

    customer_resolver = FakeInvoiceIssuedCustomerResolver(
        InvoiceIssuedCustomer(
            id=customer_id,
            email=" billing@example.com ",
        )
    )
    create_notification = FakeCreateNotificationFromIntentUseCase()

    handler = InvoiceIssuedOutboxHandler(
        customer_resolver=customer_resolver,
        create_notification=create_notification,
    )

    message = make_message(
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        customer_id=customer_id,
    )

    await handler.handle(message)

    assert customer_resolver.calls == [
        (
            tenant_id,
            customer_id,
        )
    ]

    assert len(create_notification.calls) == 1

    notification_tenant_id, intent = create_notification.calls[0]

    assert notification_tenant_id == tenant_id
    assert intent.event_type == "invoice.issued"
    assert intent.recipient == "billing@example.com"
    assert intent.channel == NotificationChannel.EMAIL
    assert intent.subject == "Invoice INV-1001 issued"
    assert intent.body == "Invoice INV-1001 has been issued. Total: 110.00 USD."
    assert intent.idempotency_key == f"invoice-issued:{invoice_id}"
    assert intent.scheduled_at is None


async def test_invoice_issued_handler_is_deterministically_idempotent() -> None:
    tenant_id = uuid4()
    invoice_id = uuid4()
    customer_id = uuid4()

    customer_resolver = FakeInvoiceIssuedCustomerResolver(
        InvoiceIssuedCustomer(
            id=customer_id,
            email="billing@example.com",
        )
    )
    create_notification = FakeCreateNotificationFromIntentUseCase()

    handler = InvoiceIssuedOutboxHandler(
        customer_resolver=customer_resolver,
        create_notification=create_notification,
    )

    first_message = make_message(
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        customer_id=customer_id,
    )
    second_message = make_message(
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        customer_id=customer_id,
    )

    await handler.handle(first_message)
    await handler.handle(second_message)

    assert len(create_notification.calls) == 2

    first_intent = create_notification.calls[0][1]
    second_intent = create_notification.calls[1][1]

    assert (
        first_intent.idempotency_key
        == second_intent.idempotency_key
        == f"invoice-issued:{invoice_id}"
    )


async def test_invoice_issued_handler_rejects_missing_customer() -> None:
    tenant_id = uuid4()
    invoice_id = uuid4()
    customer_id = uuid4()

    customer_resolver = FakeInvoiceIssuedCustomerResolver(None)
    create_notification = FakeCreateNotificationFromIntentUseCase()

    handler = InvoiceIssuedOutboxHandler(
        customer_resolver=customer_resolver,
        create_notification=create_notification,
    )

    message = make_message(
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        customer_id=customer_id,
    )

    with pytest.raises(
        InvoiceIssuedCustomerNotFoundError,
        match="not found",
    ):
        await handler.handle(message)

    assert create_notification.calls == []


async def test_invoice_issued_handler_rejects_customer_without_email() -> None:
    tenant_id = uuid4()
    invoice_id = uuid4()
    customer_id = uuid4()

    customer_resolver = FakeInvoiceIssuedCustomerResolver(
        InvoiceIssuedCustomer(
            id=customer_id,
            email=None,
        )
    )
    create_notification = FakeCreateNotificationFromIntentUseCase()

    handler = InvoiceIssuedOutboxHandler(
        customer_resolver=customer_resolver,
        create_notification=create_notification,
    )

    message = make_message(
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        customer_id=customer_id,
    )

    with pytest.raises(
        InvoiceIssuedCustomerHasNoEmailError,
        match="does not have an email",
    ):
        await handler.handle(message)

    assert create_notification.calls == []


async def test_invoice_issued_handler_rejects_blank_customer_email() -> None:
    tenant_id = uuid4()
    invoice_id = uuid4()
    customer_id = uuid4()

    customer_resolver = FakeInvoiceIssuedCustomerResolver(
        InvoiceIssuedCustomer(
            id=customer_id,
            email="   ",
        )
    )
    create_notification = FakeCreateNotificationFromIntentUseCase()

    handler = InvoiceIssuedOutboxHandler(
        customer_resolver=customer_resolver,
        create_notification=create_notification,
    )

    message = make_message(
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        customer_id=customer_id,
    )

    with pytest.raises(
        InvoiceIssuedCustomerHasNoEmailError,
        match="does not have an email",
    ):
        await handler.handle(message)

    assert create_notification.calls == []


@pytest.mark.parametrize(
    "field",
    [
        "invoice_id",
        "customer_id",
        "invoice_number",
        "currency",
        "total_amount",
    ],
)
async def test_invoice_issued_handler_rejects_missing_required_payload_field(
    field: str,
) -> None:
    tenant_id = uuid4()
    invoice_id = uuid4()
    customer_id = uuid4()

    customer_resolver = FakeInvoiceIssuedCustomerResolver(
        InvoiceIssuedCustomer(
            id=customer_id,
            email="billing@example.com",
        )
    )
    create_notification = FakeCreateNotificationFromIntentUseCase()

    handler = InvoiceIssuedOutboxHandler(
        customer_resolver=customer_resolver,
        create_notification=create_notification,
    )

    message = make_message(
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        customer_id=customer_id,
    )

    del message.payload[field]

    with pytest.raises(
        InvalidInvoiceIssuedOutboxPayloadError,
        match=field,
    ):
        await handler.handle(message)

    assert create_notification.calls == []


@pytest.mark.parametrize(
    "field",
    [
        "invoice_id",
        "customer_id",
    ],
)
async def test_invoice_issued_handler_rejects_invalid_uuid(
    field: str,
) -> None:
    tenant_id = uuid4()
    invoice_id = uuid4()
    customer_id = uuid4()

    customer_resolver = FakeInvoiceIssuedCustomerResolver(
        InvoiceIssuedCustomer(
            id=customer_id,
            email="billing@example.com",
        )
    )
    create_notification = FakeCreateNotificationFromIntentUseCase()

    handler = InvoiceIssuedOutboxHandler(
        customer_resolver=customer_resolver,
        create_notification=create_notification,
    )

    message = make_message(
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        customer_id=customer_id,
    )

    message.payload[field] = "not-a-uuid"

    with pytest.raises(
        InvalidInvoiceIssuedOutboxPayloadError,
        match="valid UUID",
    ):
        await handler.handle(message)

    assert create_notification.calls == []
