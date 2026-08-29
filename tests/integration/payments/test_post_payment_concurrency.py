import asyncio
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.billing.domain.enums import InvoiceStatus
from app.modules.billing.infrastructure.models.invoice import Invoice
from app.modules.customers.domain.enums import CustomerStatus
from app.modules.customers.infrastructure.models.customer import Customer
from app.modules.identity.domain.enums import TenantStatus
from app.modules.identity.infrastructure.models.tenant import Tenant
from app.modules.ledger.domain.enums import (
    JournalSourceType,
    LedgerAccountPurpose,
    LedgerAccountStatus,
    LedgerAccountType,
)
from app.modules.ledger.infrastructure.models import (
    JournalEntry,
    JournalLine,
    LedgerAccount,
)
from app.modules.payments.application.use_cases.post_payment import (
    PostPaymentUseCase,
)
from app.modules.payments.domain.enums import PaymentMethod, PaymentStatus
from app.modules.payments.domain.exceptions import (
    InvalidInvoiceForPaymentError,
)
from app.modules.payments.infrastructure.models.payment import Payment
from app.modules.payments.infrastructure.models.payment_allocation import (
    PaymentAllocation,
)
from app.modules.payments.infrastructure.unit_of_work import (
    SQLAlchemyPaymentsUnitOfWork,
)


@pytest.mark.integration
async def test_concurrent_post_payments_do_not_overpay_invoice(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    unique = uuid4()

    tenant_id: UUID | None = None
    customer_id: UUID | None = None
    invoice_id: UUID | None = None
    payment_a_id: UUID | None = None
    payment_b_id: UUID | None = None

    async with session_factory() as setup_session:
        tenant = Tenant(
            name=f"Payments Concurrency Tenant {unique}",
            slug=f"payments-concurrency-{unique}",
            status=TenantStatus.ACTIVE,
        )
        setup_session.add(tenant)
        await setup_session.flush()

        customer = Customer(
            tenant_id=tenant.id,
            name="Payments Concurrency Customer",
            code=f"PAY-CONC-{unique}",
            status=CustomerStatus.ACTIVE,
        )
        setup_session.add(customer)
        await setup_session.flush()

        invoice = Invoice(
            tenant_id=tenant.id,
            customer_id=customer.id,
            invoice_number=f"INV-CONC-{unique}",
            status=InvoiceStatus.ISSUED,
            currency="USD",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("100.00"),
        )
        setup_session.add(invoice)
        await setup_session.flush()

        cash_account = LedgerAccount(
            tenant_id=tenant.id,
            code="1000",
            name="Cash",
            type=LedgerAccountType.ASSET.value,
            purpose=LedgerAccountPurpose.CASH.value,
            status=LedgerAccountStatus.ACTIVE.value,
        )

        accounts_receivable = LedgerAccount(
            tenant_id=tenant.id,
            code="1100",
            name="Accounts Receivable",
            type=LedgerAccountType.ASSET.value,
            purpose=LedgerAccountPurpose.ACCOUNTS_RECEIVABLE.value,
            status=LedgerAccountStatus.ACTIVE.value,
        )

        setup_session.add_all(
            [
                cash_account,
                accounts_receivable,
            ]
        )

        payment_a = Payment(
            tenant_id=tenant.id,
            customer_id=customer.id,
            payment_number=f"PAY-CONC-A-{unique}",
            status=PaymentStatus.DRAFT,
            currency="USD",
            amount=Decimal("100.00"),
            method=PaymentMethod.BANK_TRANSFER,
        )

        payment_b = Payment(
            tenant_id=tenant.id,
            customer_id=customer.id,
            payment_number=f"PAY-CONC-B-{unique}",
            status=PaymentStatus.DRAFT,
            currency="USD",
            amount=Decimal("100.00"),
            method=PaymentMethod.BANK_TRANSFER,
        )

        setup_session.add_all(
            [
                payment_a,
                payment_b,
            ]
        )
        await setup_session.flush()

        allocation_a = PaymentAllocation(
            tenant_id=tenant.id,
            payment_id=payment_a.id,
            invoice_id=invoice.id,
            amount=Decimal("100.00"),
        )

        allocation_b = PaymentAllocation(
            tenant_id=tenant.id,
            payment_id=payment_b.id,
            invoice_id=invoice.id,
            amount=Decimal("100.00"),
        )

        setup_session.add_all(
            [
                allocation_a,
                allocation_b,
            ]
        )

        await setup_session.commit()

        tenant_id = tenant.id
        customer_id = customer.id
        invoice_id = invoice.id
        payment_a_id = payment_a.id
        payment_b_id = payment_b.id

    assert tenant_id is not None
    assert customer_id is not None
    assert invoice_id is not None
    assert payment_a_id is not None
    assert payment_b_id is not None

    async def post_payment(payment_id: UUID) -> object:
        unit_of_work = SQLAlchemyPaymentsUnitOfWork(session_factory)
        use_case = PostPaymentUseCase(unit_of_work)

        return await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment_id,
        )

    try:
        results = await asyncio.gather(
            post_payment(payment_a_id),
            post_payment(payment_b_id),
            return_exceptions=True,
        )

        successful_results = [result for result in results if isinstance(result, Payment)]
        failed_results = [result for result in results if isinstance(result, BaseException)]

        assert len(successful_results) == 1
        assert len(failed_results) == 1
        assert isinstance(
            failed_results[0],
            InvalidInvoiceForPaymentError,
        )

        async with session_factory() as verification_session:
            persisted_invoice = await verification_session.scalar(
                select(Invoice).where(
                    Invoice.tenant_id == tenant_id,
                    Invoice.id == invoice_id,
                )
            )

            assert persisted_invoice is not None
            assert persisted_invoice.status == InvoiceStatus.PAID
            assert persisted_invoice.paid_at is not None

            persisted_payments = list(
                (
                    await verification_session.scalars(
                        select(Payment)
                        .where(
                            Payment.tenant_id == tenant_id,
                            Payment.id.in_(
                                [
                                    payment_a_id,
                                    payment_b_id,
                                ]
                            ),
                        )
                        .order_by(Payment.payment_number)
                    )
                ).all()
            )

            assert len(persisted_payments) == 2

            posted_payments = [
                payment for payment in persisted_payments if payment.status == PaymentStatus.POSTED
            ]
            draft_payments = [
                payment for payment in persisted_payments if payment.status == PaymentStatus.DRAFT
            ]

            assert len(posted_payments) == 1
            assert len(draft_payments) == 1

            posted_payment = posted_payments[0]
            draft_payment = draft_payments[0]

            posted_allocations = list(
                (
                    await verification_session.scalars(
                        select(PaymentAllocation).where(
                            PaymentAllocation.tenant_id == tenant_id,
                            PaymentAllocation.invoice_id == invoice_id,
                            PaymentAllocation.payment_id == posted_payment.id,
                        )
                    )
                ).all()
            )

            posted_total = sum(
                (allocation.amount for allocation in posted_allocations),
                Decimal("0.00"),
            )

            assert posted_total == Decimal("100.00")

            journal_entries = list(
                (
                    await verification_session.scalars(
                        select(JournalEntry).where(
                            JournalEntry.tenant_id == tenant_id,
                            JournalEntry.source_type == JournalSourceType.PAYMENT_POSTED.value,
                        )
                    )
                ).all()
            )

            assert len(journal_entries) == 1

            journal_entry = journal_entries[0]

            assert journal_entry.source_id == posted_payment.id
            assert journal_entry.source_id != draft_payment.id

            journal_lines = list(
                (
                    await verification_session.scalars(
                        select(JournalLine).where(
                            JournalLine.tenant_id == tenant_id,
                            JournalLine.journal_entry_id == journal_entry.id,
                        )
                    )
                ).all()
            )

            assert len(journal_lines) == 2

            persisted_cash_account = await verification_session.scalar(
                select(LedgerAccount).where(
                    LedgerAccount.tenant_id == tenant_id,
                    LedgerAccount.purpose == LedgerAccountPurpose.CASH.value,
                )
            )
            persisted_accounts_receivable = await verification_session.scalar(
                select(LedgerAccount).where(
                    LedgerAccount.tenant_id == tenant_id,
                    LedgerAccount.purpose == LedgerAccountPurpose.ACCOUNTS_RECEIVABLE.value,
                )
            )

            assert persisted_cash_account is not None
            assert persisted_accounts_receivable is not None

            cash_line = next(
                line
                for line in journal_lines
                if line.ledger_account_id == persisted_cash_account.id
            )
            accounts_receivable_line = next(
                line
                for line in journal_lines
                if line.ledger_account_id == persisted_accounts_receivable.id
            )

            assert cash_line.debit == Decimal("100.00")
            assert cash_line.credit == Decimal("0.00")

            assert accounts_receivable_line.debit == Decimal("0.00")
            assert accounts_receivable_line.credit == Decimal("100.00")

            total_debit = sum(
                (line.debit for line in journal_lines),
                Decimal("0.00"),
            )
            total_credit = sum(
                (line.credit for line in journal_lines),
                Decimal("0.00"),
            )

            assert total_debit == Decimal("100.00")
            assert total_credit == Decimal("100.00")
            assert total_debit == total_credit

            failed_payment_journal = await verification_session.scalar(
                select(JournalEntry).where(
                    JournalEntry.tenant_id == tenant_id,
                    JournalEntry.source_type == JournalSourceType.PAYMENT_POSTED.value,
                    JournalEntry.source_id == draft_payment.id,
                )
            )

            assert failed_payment_journal is None

    finally:
        async with session_factory() as cleanup_session:
            await cleanup_session.execute(
                delete(JournalLine).where(
                    JournalLine.tenant_id == tenant_id,
                )
            )

            await cleanup_session.execute(
                delete(JournalEntry).where(
                    JournalEntry.tenant_id == tenant_id,
                )
            )

            await cleanup_session.execute(
                delete(LedgerAccount).where(
                    LedgerAccount.tenant_id == tenant_id,
                )
            )

            await cleanup_session.execute(
                delete(PaymentAllocation).where(
                    PaymentAllocation.tenant_id == tenant_id,
                )
            )

            await cleanup_session.execute(
                delete(Payment).where(
                    Payment.tenant_id == tenant_id,
                )
            )

            await cleanup_session.execute(
                delete(Invoice).where(
                    Invoice.tenant_id == tenant_id,
                )
            )

            await cleanup_session.execute(
                delete(Customer).where(
                    Customer.tenant_id == tenant_id,
                )
            )

            await cleanup_session.execute(
                delete(Tenant).where(
                    Tenant.id == tenant_id,
                )
            )

            await cleanup_session.commit()
