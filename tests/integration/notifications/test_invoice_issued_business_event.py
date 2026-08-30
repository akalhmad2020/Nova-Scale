from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.main import app
from app.modules.customers.infrastructure.models.customer import Customer
from app.modules.identity.domain.permissions import Permissions
from app.modules.notifications.domain.enums import (
    NotificationChannel,
    NotificationStatus,
)
from app.modules.notifications.infrastructure.models.notification import (
    Notification,
)
from app.modules.notifications.infrastructure.outbox.registry import (
    build_notification_outbox_handler_registry,
)
from app.shared.outbox.application.processing_service import (
    OutboxProcessingService,
)
from app.shared.outbox.application.retry_policy import OutboxRetryPolicy
from app.shared.outbox.domain.enums import OutboxMessageStatus
from app.shared.outbox.infrastructure.models.outbox_message import (
    OutboxMessage,
)
from app.shared.outbox.infrastructure.repositories.sqlalchemy import (
    SQLAlchemyOutboxMessageRepository,
)
from app.shared.outbox.infrastructure.unit_of_work import (
    SQLAlchemyOutboxUnitOfWork,
)
from tests.integration.billing.test_invoice_lifecycle_api import (
    cleanup_test_data,
    create_invoice,
    create_ledger_system_accounts,
    create_lifecycle_context,
    login_and_get_access_token,
)

pytestmark = pytest.mark.integration

EVENT_TYPE = "invoice.issued"


async def set_customer_email(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    customer_id: UUID,
    email: str | None,
) -> None:
    async with session_factory() as session:
        customer = await session.get(
            Customer,
            customer_id,
        )

        assert customer is not None

        customer.email = email

        await session.commit()


async def clear_notification_outbox_data(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    tenant_id: UUID,
) -> None:
    async with session_factory() as session:
        await session.execute(
            delete(Notification).where(
                Notification.tenant_id == tenant_id,
            )
        )

        await session.execute(
            delete(OutboxMessage).where(
                OutboxMessage.tenant_id == tenant_id,
            )
        )

        await session.commit()


async def get_invoice_issued_outbox_message(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    tenant_id: UUID,
    invoice_id: UUID,
) -> OutboxMessage:
    async with session_factory() as session:
        messages = list(
            (
                await session.scalars(
                    select(OutboxMessage)
                    .where(
                        OutboxMessage.tenant_id == tenant_id,
                        OutboxMessage.event_type == EVENT_TYPE,
                    )
                    .order_by(OutboxMessage.created_at)
                )
            ).all()
        )

        matching_messages = [
            message for message in messages if message.payload.get("invoice_id") == str(invoice_id)
        ]

        assert len(matching_messages) == 1

        return matching_messages[0]


async def get_notification(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    tenant_id: UUID,
    invoice_id: UUID,
) -> Notification | None:
    idempotency_key = f"invoice-issued:{invoice_id}"

    async with session_factory() as session:
        result = await session.scalars(
            select(Notification).where(
                Notification.tenant_id == tenant_id,
                Notification.idempotency_key == idempotency_key,
            )
        )

        return result.one_or_none()


async def get_outbox_message(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    message_id: UUID,
) -> OutboxMessage | None:
    async with session_factory() as session:
        repository = SQLAlchemyOutboxMessageRepository(
            session,
        )

        return await repository.get_by_id(
            message_id=message_id,
        )


def build_processing_service(
    session_factory: async_sessionmaker[AsyncSession],
) -> OutboxProcessingService:
    registry = build_notification_outbox_handler_registry(
        session_factory,
    )

    return OutboxProcessingService(
        unit_of_work_factory=lambda: SQLAlchemyOutboxUnitOfWork(
            session_factory,
        ),
        handler_resolver=registry,
        retry_policy=OutboxRetryPolicy(
            max_attempts=3,
            base_delay=timedelta(seconds=30),
            max_delay=timedelta(minutes=5),
        ),
        lease_duration=timedelta(minutes=5),
        batch_size=10,
    )


async def issue_invoice_via_api(
    *,
    tenant_id: UUID,
    invoice_id: UUID,
    email: str,
    password: str,
) -> None:
    access_token = login_and_get_access_token(
        email=email,
        password=password,
    )

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/tenants/{tenant_id}/invoices/{invoice_id}/issue",
            headers={
                "Authorization": f"Bearer {access_token}",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "issued"


async def test_invoice_issued_business_event_creates_notification(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    unique = uuid4()
    short_unique = unique.hex[:12]

    user_email = f"invoice-event-{short_unique}@example.com"
    customer_email = f"billing-{short_unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"invoice-event-{short_unique}"
    role_name = f"invoice-event-role-{short_unique}"

    tenant, customer = await create_lifecycle_context(
        email=user_email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_ISSUE,),
    )

    try:
        await set_customer_email(
            session_factory,
            customer_id=customer.id,
            email=customer_email,
        )

        await create_ledger_system_accounts(
            tenant_id=tenant.id,
        )

        invoice = await create_invoice(
            tenant_id=tenant.id,
            customer_id=customer.id,
            invoice_number=f"INV-EVT-{short_unique}",
            with_line=True,
        )

        await issue_invoice_via_api(
            tenant_id=tenant.id,
            invoice_id=invoice.id,
            email=user_email,
            password=password,
        )

        outbox_before_processing = await get_invoice_issued_outbox_message(
            session_factory,
            tenant_id=tenant.id,
            invoice_id=invoice.id,
        )

        assert outbox_before_processing.status == OutboxMessageStatus.PENDING.value
        assert outbox_before_processing.attempt_count == 0
        assert outbox_before_processing.processed_at is None
        assert outbox_before_processing.claim_token is None
        assert outbox_before_processing.lease_expires_at is None

        assert outbox_before_processing.payload["invoice_id"] == str(invoice.id)
        assert outbox_before_processing.payload["customer_id"] == str(customer.id)
        assert outbox_before_processing.payload["invoice_number"] == f"INV-EVT-{short_unique}"
        assert outbox_before_processing.payload["currency"] == "USD"
        assert outbox_before_processing.payload["subtotal"] == "25.00"
        assert outbox_before_processing.payload["tax_amount"] == "5.00"
        assert outbox_before_processing.payload["total_amount"] == "30.00"

        notification_before_processing = await get_notification(
            session_factory,
            tenant_id=tenant.id,
            invoice_id=invoice.id,
        )

        assert notification_before_processing is None

        service = build_processing_service(
            session_factory,
        )

        now = datetime.now(UTC)

        processed_count = await service.process_batch(
            now=now,
        )

        assert processed_count == 1

        outbox_after_processing = await get_outbox_message(
            session_factory,
            message_id=outbox_before_processing.id,
        )

        assert outbox_after_processing is not None
        assert outbox_after_processing.status == OutboxMessageStatus.PROCESSED.value
        assert outbox_after_processing.attempt_count == 1
        assert outbox_after_processing.processed_at == now
        assert outbox_after_processing.claim_token is None
        assert outbox_after_processing.lease_expires_at is None
        assert outbox_after_processing.last_error is None

        notification = await get_notification(
            session_factory,
            tenant_id=tenant.id,
            invoice_id=invoice.id,
        )

        assert notification is not None
        assert notification.tenant_id == tenant.id
        assert notification.event_type == EVENT_TYPE
        assert notification.recipient == customer_email
        assert notification.channel == NotificationChannel.EMAIL.value
        assert notification.subject == f"Invoice INV-EVT-{short_unique} issued"
        assert notification.body == (
            f"Invoice INV-EVT-{short_unique} has been issued. Total: 30.00 USD."
        )
        assert notification.status == NotificationStatus.PENDING.value
        assert notification.idempotency_key == f"invoice-issued:{invoice.id}"
        assert notification.scheduled_at is None
        assert notification.sent_at is None
        assert notification.failed_at is None
        assert notification.failure_reason is None

    finally:
        await clear_notification_outbox_data(
            session_factory,
            tenant_id=tenant.id,
        )

        await cleanup_test_data(
            email=user_email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


async def test_invoice_issued_without_customer_email_is_released_for_retry(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    unique = uuid4()
    short_unique = unique.hex[:12]

    user_email = f"invoice-retry-{short_unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"invoice-retry-{short_unique}"
    role_name = f"invoice-retry-role-{short_unique}"

    tenant, customer = await create_lifecycle_context(
        email=user_email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_ISSUE,),
    )

    try:
        await set_customer_email(
            session_factory,
            customer_id=customer.id,
            email=None,
        )

        await create_ledger_system_accounts(
            tenant_id=tenant.id,
        )

        invoice = await create_invoice(
            tenant_id=tenant.id,
            customer_id=customer.id,
            invoice_number=f"INV-RTY-{short_unique}",
            with_line=True,
        )

        await issue_invoice_via_api(
            tenant_id=tenant.id,
            invoice_id=invoice.id,
            email=user_email,
            password=password,
        )

        outbox_before_processing = await get_invoice_issued_outbox_message(
            session_factory,
            tenant_id=tenant.id,
            invoice_id=invoice.id,
        )

        assert outbox_before_processing.status == OutboxMessageStatus.PENDING.value

        service = build_processing_service(
            session_factory,
        )

        now = datetime.now(UTC)

        processed_count = await service.process_batch(
            now=now,
        )

        assert processed_count == 1

        outbox_after_processing = await get_outbox_message(
            session_factory,
            message_id=outbox_before_processing.id,
        )

        assert outbox_after_processing is not None

        assert outbox_after_processing.status == OutboxMessageStatus.PENDING.value
        assert outbox_after_processing.attempt_count == 1
        assert outbox_after_processing.processed_at is None
        assert outbox_after_processing.claim_token is None
        assert outbox_after_processing.lease_expires_at is None

        assert outbox_after_processing.available_at == now + timedelta(seconds=30)

        assert outbox_after_processing.last_error is not None
        assert "does not have an email" in outbox_after_processing.last_error

        notification = await get_notification(
            session_factory,
            tenant_id=tenant.id,
            invoice_id=invoice.id,
        )

        assert notification is None

    finally:
        await clear_notification_outbox_data(
            session_factory,
            tenant_id=tenant.id,
        )

        await cleanup_test_data(
            email=user_email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )
