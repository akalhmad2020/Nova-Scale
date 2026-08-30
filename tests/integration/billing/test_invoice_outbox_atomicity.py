from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.modules.billing.application.use_cases.issue_invoice import (
    INVOICE_ISSUED_EVENT_TYPE,
    IssueInvoiceUseCase,
)
from app.modules.billing.domain.enums import InvoiceStatus
from app.modules.billing.infrastructure.models.invoice import Invoice
from app.modules.billing.infrastructure.unit_of_work import (
    SQLAlchemyBillingUnitOfWork,
)
from app.modules.ledger.domain.enums import JournalSourceType
from app.modules.ledger.infrastructure.models import (
    JournalEntry,
    JournalLine,
)
from app.shared.outbox.domain.enums import OutboxMessageStatus
from app.shared.outbox.infrastructure.models.outbox_message import (
    OutboxMessage,
)
from app.shared.outbox.infrastructure.repositories.sqlalchemy import (
    SQLAlchemyOutboxMessageRepository,
)
from tests.integration.billing.test_invoice_lifecycle_api import (
    cleanup_test_data,
    create_invoice,
    create_ledger_system_accounts,
    create_lifecycle_context,
)

pytestmark = pytest.mark.integration


async def delete_outbox_messages(
    *,
    tenant_id: UUID,
) -> None:
    settings = get_settings()

    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    try:
        async with session_factory() as session:
            await session.execute(
                delete(OutboxMessage).where(
                    OutboxMessage.tenant_id == tenant_id,
                )
            )
            await session.commit()
    finally:
        await engine.dispose()


async def cleanup_context(
    *,
    tenant_id: UUID,
    email: str,
    tenant_slug: str,
    role_name: str,
) -> None:
    await delete_outbox_messages(
        tenant_id=tenant_id,
    )

    await cleanup_test_data(
        email=email,
        tenant_slugs=(tenant_slug,),
        role_name=role_name,
    )


async def test_issue_invoice_commits_invoice_ledger_and_outbox_atomically() -> None:
    unique = uuid4()
    short_unique = unique.hex[:12]

    email = f"billing-outbox-success-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-outbox-success-tenant-{unique}"
    role_name = f"billing-outbox-success-role-{unique}"

    tenant, customer = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(),
    )

    await create_ledger_system_accounts(
        tenant_id=tenant.id,
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number=f"INV-OUT-{short_unique}",
        with_line=True,
    )

    settings = get_settings()

    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    try:
        use_case = IssueInvoiceUseCase(
            SQLAlchemyBillingUnitOfWork(
                session_factory,
            )
        )

        result = await use_case.execute(
            tenant_id=tenant.id,
            invoice_id=invoice.id,
            actor_id=uuid4(),
        )

        assert result.status == InvoiceStatus.ISSUED.value
        assert result.issued_at is not None

        async with session_factory() as session:
            persisted_invoice = await session.scalar(
                select(Invoice).where(
                    Invoice.id == invoice.id,
                    Invoice.tenant_id == tenant.id,
                )
            )

            journal_entry = await session.scalar(
                select(JournalEntry).where(
                    JournalEntry.tenant_id == tenant.id,
                    JournalEntry.source_type == JournalSourceType.INVOICE_ISSUED.value,
                    JournalEntry.source_id == invoice.id,
                )
            )

            outbox_message = await session.scalar(
                select(OutboxMessage).where(
                    OutboxMessage.tenant_id == tenant.id,
                    OutboxMessage.event_type == INVOICE_ISSUED_EVENT_TYPE,
                )
            )

            assert persisted_invoice is not None
            assert persisted_invoice.status == InvoiceStatus.ISSUED.value
            assert persisted_invoice.issued_at is not None

            assert journal_entry is not None
            assert journal_entry.source_id == invoice.id

            assert outbox_message is not None
            assert outbox_message.status == OutboxMessageStatus.PENDING.value
            assert outbox_message.attempt_count == 0

            assert outbox_message.payload["invoice_id"] == str(invoice.id)
            assert outbox_message.payload["customer_id"] == str(customer.id)
            assert outbox_message.payload["invoice_number"] == invoice.invoice_number
            assert outbox_message.payload["currency"] == invoice.currency
            assert outbox_message.payload["subtotal"] == str(invoice.subtotal)
            assert outbox_message.payload["tax_amount"] == str(invoice.tax_amount)
            assert outbox_message.payload["total_amount"] == str(invoice.total_amount)

    finally:
        await engine.dispose()

        await cleanup_context(
            tenant_id=tenant.id,
            email=email,
            tenant_slug=tenant_slug,
            role_name=role_name,
        )


async def test_issue_invoice_rolls_back_invoice_and_ledger_when_outbox_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unique = uuid4()
    short_unique = unique.hex[:12]

    email = f"billing-outbox-rollback-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-outbox-rollback-tenant-{unique}"
    role_name = f"billing-outbox-rollback-role-{unique}"

    tenant, customer = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(),
    )

    await create_ledger_system_accounts(
        tenant_id=tenant.id,
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number=f"INV-RB-{short_unique}",
        with_line=True,
    )

    async def failing_add(
        self: SQLAlchemyOutboxMessageRepository,
        message: OutboxMessage,
    ) -> None:
        raise RuntimeError("Forced outbox persistence failure.")

    monkeypatch.setattr(
        SQLAlchemyOutboxMessageRepository,
        "add",
        failing_add,
    )

    settings = get_settings()

    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    try:
        use_case = IssueInvoiceUseCase(
            SQLAlchemyBillingUnitOfWork(
                session_factory,
            )
        )

        with pytest.raises(
            RuntimeError,
            match="Forced outbox persistence failure",
        ):
            await use_case.execute(
                tenant_id=tenant.id,
                invoice_id=invoice.id,
                actor_id=uuid4(),
            )

        async with session_factory() as verification_session:
            persisted_invoice = await verification_session.scalar(
                select(Invoice).where(
                    Invoice.id == invoice.id,
                    Invoice.tenant_id == tenant.id,
                )
            )

            journal_entry = await verification_session.scalar(
                select(JournalEntry).where(
                    JournalEntry.tenant_id == tenant.id,
                    JournalEntry.source_type == JournalSourceType.INVOICE_ISSUED.value,
                    JournalEntry.source_id == invoice.id,
                )
            )

            outbox_message = await verification_session.scalar(
                select(OutboxMessage).where(
                    OutboxMessage.tenant_id == tenant.id,
                    OutboxMessage.event_type == INVOICE_ISSUED_EVENT_TYPE,
                )
            )

            journal_lines = list(
                (
                    await verification_session.scalars(
                        select(JournalLine).where(
                            JournalLine.tenant_id == tenant.id,
                        )
                    )
                ).all()
            )

            assert persisted_invoice is not None
            assert persisted_invoice.status == InvoiceStatus.DRAFT.value
            assert persisted_invoice.issued_at is None

            assert journal_entry is None
            assert journal_lines == []
            assert outbox_message is None

    finally:
        await engine.dispose()

        await cleanup_context(
            tenant_id=tenant.id,
            email=email,
            tenant_slug=tenant_slug,
            role_name=role_name,
        )
