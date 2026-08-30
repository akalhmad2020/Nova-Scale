from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.audit.domain.enums import AuditActorType, AuditOutcome
from app.modules.billing.application.exceptions import (
    CustomerNotFoundError,
    InvalidInvoiceAmountError,
    InvalidInvoiceStateTransitionError,
    InvoiceHasNoLinesError,
    InvoiceLineNotFoundError,
    InvoiceNotEditableError,
    InvoiceNotFoundError,
    InvoiceNumberAlreadyExistsError,
    ShipmentNotFoundError,
)
from app.modules.billing.application.use_cases.add_invoice_line import (
    AddInvoiceLineUseCase,
)
from app.modules.billing.application.use_cases.create_invoice import (
    CreateInvoiceUseCase,
)
from app.modules.billing.application.use_cases.get_invoice import (
    GetInvoiceUseCase,
)
from app.modules.billing.application.use_cases.issue_invoice import (
    IssueInvoiceUseCase,
)
from app.modules.billing.application.use_cases.list_invoices import (
    ListInvoicesUseCase,
)
from app.modules.billing.application.use_cases.remove_invoice_line import (
    RemoveInvoiceLineUseCase,
)
from app.modules.billing.application.use_cases.void_invoice import (
    VoidInvoiceUseCase,
)
from app.modules.billing.domain.enums import InvoiceStatus
from app.modules.ledger.domain.enums import (
    LedgerAccountPurpose,
    LedgerAccountStatus,
    LedgerAccountType,
)
from app.modules.ledger.infrastructure.models import LedgerAccount
from tests.unit.billing.fakes import FakeBillingUnitOfWork


def add_customer(
    unit_of_work: FakeBillingUnitOfWork,
    *,
    tenant_id: UUID,
) -> UUID:
    customer_id = uuid4()

    unit_of_work.fake_customers.add_existing(
        customer_id=customer_id,
        tenant_id=tenant_id,
    )

    return customer_id


def add_invoice_ledger_accounts(
    unit_of_work: FakeBillingUnitOfWork,
    *,
    tenant_id: UUID,
) -> None:
    unit_of_work.fake_ledger_accounts.items.extend(
        [
            LedgerAccount(
                id=uuid4(),
                tenant_id=tenant_id,
                code="1100",
                name="Accounts Receivable",
                type=LedgerAccountType.ASSET.value,
                purpose=LedgerAccountPurpose.ACCOUNTS_RECEIVABLE.value,
                status=LedgerAccountStatus.ACTIVE.value,
            ),
            LedgerAccount(
                id=uuid4(),
                tenant_id=tenant_id,
                code="4000",
                name="Revenue",
                type=LedgerAccountType.REVENUE.value,
                purpose=LedgerAccountPurpose.REVENUE.value,
                status=LedgerAccountStatus.ACTIVE.value,
            ),
        ]
    )


@pytest.mark.asyncio
async def test_create_invoice() -> None:
    tenant_id = uuid4()

    unit_of_work = FakeBillingUnitOfWork()
    customer_id = add_customer(unit_of_work, tenant_id=tenant_id)
    use_case = CreateInvoiceUseCase(unit_of_work)

    invoice = await use_case.execute(
        tenant_id=tenant_id,
        customer_id=customer_id,
        invoice_number="INV-0001",
        currency="usd",
        tax_amount=Decimal("10.00"),
    )

    assert invoice.tenant_id == tenant_id
    assert invoice.customer_id == customer_id
    assert invoice.invoice_number == "INV-0001"
    assert invoice.currency == "USD"
    assert invoice.status == InvoiceStatus.DRAFT

    assert invoice.subtotal == Decimal("0.00")
    assert invoice.tax_amount == Decimal("10.00")
    assert invoice.total_amount == Decimal("10.00")

    assert unit_of_work.committed is True
    assert len(unit_of_work.fake_invoices.items) == 1


@pytest.mark.asyncio
async def test_create_invoice_trims_invoice_number() -> None:
    tenant_id = uuid4()
    unit_of_work = FakeBillingUnitOfWork()
    use_case = CreateInvoiceUseCase(unit_of_work)

    invoice = await use_case.execute(
        tenant_id=tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=tenant_id),
        invoice_number="  INV-0001  ",
        currency="usd",
    )

    assert invoice.invoice_number == "INV-0001"


@pytest.mark.asyncio
async def test_create_invoice_normalizes_currency() -> None:
    tenant_id = uuid4()
    unit_of_work = FakeBillingUnitOfWork()
    use_case = CreateInvoiceUseCase(unit_of_work)

    invoice = await use_case.execute(
        tenant_id=tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=tenant_id),
        invoice_number="INV-0001",
        currency=" usd ",
    )

    assert invoice.currency == "USD"


@pytest.mark.asyncio
async def test_create_invoice_rejects_negative_tax() -> None:
    unit_of_work = FakeBillingUnitOfWork()
    use_case = CreateInvoiceUseCase(unit_of_work)

    with pytest.raises(InvalidInvoiceAmountError):
        await use_case.execute(
            tenant_id=uuid4(),
            customer_id=uuid4(),
            invoice_number="INV-0001",
            currency="USD",
            tax_amount=Decimal("-0.01"),
        )

    assert unit_of_work.committed is False


@pytest.mark.asyncio
async def test_create_invoice_rejects_duplicate_number_per_tenant() -> None:
    tenant_id = uuid4()

    unit_of_work = FakeBillingUnitOfWork()
    use_case = CreateInvoiceUseCase(unit_of_work)

    await use_case.execute(
        tenant_id=tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=tenant_id),
        invoice_number="INV-0001",
        currency="USD",
    )

    unit_of_work.committed = False

    with pytest.raises(InvoiceNumberAlreadyExistsError):
        await use_case.execute(
            tenant_id=tenant_id,
            customer_id=add_customer(unit_of_work, tenant_id=tenant_id),
            invoice_number="INV-0001",
            currency="USD",
        )

    assert len(unit_of_work.fake_invoices.items) == 1


@pytest.mark.asyncio
async def test_create_invoice_rejects_missing_customer() -> None:
    tenant_id = uuid4()

    unit_of_work = FakeBillingUnitOfWork()
    use_case = CreateInvoiceUseCase(unit_of_work)

    with pytest.raises(CustomerNotFoundError):
        await use_case.execute(
            tenant_id=tenant_id,
            customer_id=uuid4(),
            invoice_number="INV-0001",
            currency="USD",
        )

    assert unit_of_work.committed is False
    assert len(unit_of_work.fake_invoices.items) == 0


@pytest.mark.asyncio
async def test_create_invoice_rejects_customer_from_foreign_tenant() -> None:
    tenant_id = uuid4()
    foreign_tenant_id = uuid4()
    customer_id = uuid4()

    unit_of_work = FakeBillingUnitOfWork()

    unit_of_work.fake_customers.add_existing(
        customer_id=customer_id,
        tenant_id=foreign_tenant_id,
    )

    use_case = CreateInvoiceUseCase(unit_of_work)

    with pytest.raises(CustomerNotFoundError):
        await use_case.execute(
            tenant_id=tenant_id,
            customer_id=customer_id,
            invoice_number="INV-0001",
            currency="USD",
        )

    assert unit_of_work.committed is False
    assert len(unit_of_work.fake_invoices.items) == 0


@pytest.mark.asyncio
async def test_add_invoice_line_updates_invoice_totals() -> None:
    tenant_id = uuid4()

    unit_of_work = FakeBillingUnitOfWork()

    create_invoice = CreateInvoiceUseCase(unit_of_work)
    add_line = AddInvoiceLineUseCase(unit_of_work)

    invoice = await create_invoice.execute(
        tenant_id=tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=tenant_id),
        invoice_number="INV-0001",
        currency="USD",
        tax_amount=Decimal("5.00"),
    )

    unit_of_work.committed = False

    invoice_line = await add_line.execute(
        tenant_id=tenant_id,
        invoice_id=invoice.id,
        description="Shipping service",
        quantity=Decimal("2.0000"),
        unit_price=Decimal("10.50"),
    )

    assert invoice_line.description == "Shipping service"
    assert invoice_line.quantity == Decimal("2.0000")
    assert invoice_line.unit_price == Decimal("10.50")
    assert invoice_line.amount == Decimal("21.00")

    assert invoice.subtotal == Decimal("21.00")
    assert invoice.total_amount == Decimal("26.00")

    assert len(unit_of_work.fake_invoice_lines.items) == 1
    assert unit_of_work.committed is True


@pytest.mark.asyncio
async def test_add_invoice_line_uses_money_rounding_policy() -> None:
    tenant_id = uuid4()

    unit_of_work = FakeBillingUnitOfWork()

    create_invoice = CreateInvoiceUseCase(unit_of_work)
    add_line = AddInvoiceLineUseCase(unit_of_work)

    invoice = await create_invoice.execute(
        tenant_id=tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=tenant_id),
        invoice_number="INV-0001",
        currency="USD",
    )

    invoice_line = await add_line.execute(
        tenant_id=tenant_id,
        invoice_id=invoice.id,
        description="Fractional shipping service",
        quantity=Decimal("1.2345"),
        unit_price=Decimal("10.99"),
    )

    assert invoice_line.amount == Decimal("13.57")
    assert invoice.subtotal == Decimal("13.57")
    assert invoice.total_amount == Decimal("13.57")


@pytest.mark.asyncio
async def test_add_multiple_invoice_lines_updates_subtotal() -> None:
    tenant_id = uuid4()

    unit_of_work = FakeBillingUnitOfWork()

    create_invoice = CreateInvoiceUseCase(unit_of_work)
    add_line = AddInvoiceLineUseCase(unit_of_work)

    invoice = await create_invoice.execute(
        tenant_id=tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=tenant_id),
        invoice_number="INV-0001",
        currency="USD",
        tax_amount=Decimal("3.00"),
    )

    await add_line.execute(
        tenant_id=tenant_id,
        invoice_id=invoice.id,
        description="First service",
        quantity=Decimal("2.0000"),
        unit_price=Decimal("10.00"),
    )

    await add_line.execute(
        tenant_id=tenant_id,
        invoice_id=invoice.id,
        description="Second service",
        quantity=Decimal("3.0000"),
        unit_price=Decimal("5.00"),
    )

    assert invoice.subtotal == Decimal("35.00")
    assert invoice.total_amount == Decimal("38.00")
    assert len(unit_of_work.fake_invoice_lines.items) == 2


@pytest.mark.asyncio
async def test_add_invoice_line_rejects_zero_quantity() -> None:
    tenant_id = uuid4()

    unit_of_work = FakeBillingUnitOfWork()

    create_invoice = CreateInvoiceUseCase(unit_of_work)
    add_line = AddInvoiceLineUseCase(unit_of_work)

    invoice = await create_invoice.execute(
        tenant_id=tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=tenant_id),
        invoice_number="INV-0001",
        currency="USD",
    )

    with pytest.raises(InvalidInvoiceAmountError):
        await add_line.execute(
            tenant_id=tenant_id,
            invoice_id=invoice.id,
            description="Shipping service",
            quantity=Decimal("0"),
            unit_price=Decimal("10.00"),
        )


@pytest.mark.asyncio
async def test_add_invoice_line_rejects_negative_unit_price() -> None:
    tenant_id = uuid4()

    unit_of_work = FakeBillingUnitOfWork()

    create_invoice = CreateInvoiceUseCase(unit_of_work)
    add_line = AddInvoiceLineUseCase(unit_of_work)

    invoice = await create_invoice.execute(
        tenant_id=tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=tenant_id),
        invoice_number="INV-0001",
        currency="USD",
    )

    with pytest.raises(InvalidInvoiceAmountError):
        await add_line.execute(
            tenant_id=tenant_id,
            invoice_id=invoice.id,
            description="Shipping service",
            quantity=Decimal("1.0000"),
            unit_price=Decimal("-0.01"),
        )


@pytest.mark.asyncio
async def test_add_invoice_line_rejects_non_draft_invoice() -> None:
    tenant_id = uuid4()

    unit_of_work = FakeBillingUnitOfWork()

    create_invoice = CreateInvoiceUseCase(unit_of_work)
    add_line = AddInvoiceLineUseCase(unit_of_work)

    invoice = await create_invoice.execute(
        tenant_id=tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=tenant_id),
        invoice_number="INV-0001",
        currency="USD",
    )

    invoice.status = InvoiceStatus.ISSUED

    with pytest.raises(InvoiceNotEditableError):
        await add_line.execute(
            tenant_id=tenant_id,
            invoice_id=invoice.id,
            description="Shipping service",
            quantity=Decimal("1.0000"),
            unit_price=Decimal("10.00"),
        )

    assert len(unit_of_work.fake_invoice_lines.items) == 0


@pytest.mark.asyncio
async def test_add_invoice_line_accepts_shipment_from_same_tenant() -> None:
    tenant_id = uuid4()
    shipment_id = uuid4()

    unit_of_work = FakeBillingUnitOfWork()

    customer_id = add_customer(unit_of_work, tenant_id=tenant_id)
    unit_of_work.fake_shipments.add_existing(
        shipment_id=shipment_id,
        tenant_id=tenant_id,
    )

    create_invoice = CreateInvoiceUseCase(unit_of_work)
    add_line = AddInvoiceLineUseCase(unit_of_work)

    invoice = await create_invoice.execute(
        tenant_id=tenant_id,
        customer_id=customer_id,
        invoice_number="INV-0001",
        currency="USD",
    )

    invoice_line = await add_line.execute(
        tenant_id=tenant_id,
        invoice_id=invoice.id,
        shipment_id=shipment_id,
        description="Shipping service",
        quantity=Decimal("1.0000"),
        unit_price=Decimal("25.00"),
    )

    assert invoice_line.shipment_id == shipment_id


@pytest.mark.asyncio
async def test_add_invoice_line_rejects_missing_shipment() -> None:
    tenant_id = uuid4()

    unit_of_work = FakeBillingUnitOfWork()
    customer_id = add_customer(unit_of_work, tenant_id=tenant_id)

    create_invoice = CreateInvoiceUseCase(unit_of_work)
    add_line = AddInvoiceLineUseCase(unit_of_work)

    invoice = await create_invoice.execute(
        tenant_id=tenant_id,
        customer_id=customer_id,
        invoice_number="INV-0001",
        currency="USD",
    )

    with pytest.raises(ShipmentNotFoundError):
        await add_line.execute(
            tenant_id=tenant_id,
            invoice_id=invoice.id,
            shipment_id=uuid4(),
            description="Shipping service",
            quantity=Decimal("1.0000"),
            unit_price=Decimal("25.00"),
        )


@pytest.mark.asyncio
async def test_add_invoice_line_rejects_shipment_from_foreign_tenant() -> None:
    tenant_id = uuid4()
    foreign_tenant_id = uuid4()
    shipment_id = uuid4()

    unit_of_work = FakeBillingUnitOfWork()
    customer_id = add_customer(unit_of_work, tenant_id=tenant_id)

    unit_of_work.fake_shipments.add_existing(
        shipment_id=shipment_id,
        tenant_id=foreign_tenant_id,
    )

    create_invoice = CreateInvoiceUseCase(unit_of_work)
    add_line = AddInvoiceLineUseCase(unit_of_work)

    invoice = await create_invoice.execute(
        tenant_id=tenant_id,
        customer_id=customer_id,
        invoice_number="INV-0001",
        currency="USD",
    )

    with pytest.raises(ShipmentNotFoundError):
        await add_line.execute(
            tenant_id=tenant_id,
            invoice_id=invoice.id,
            shipment_id=shipment_id,
            description="Shipping service",
            quantity=Decimal("1.0000"),
            unit_price=Decimal("25.00"),
        )

    assert len(unit_of_work.fake_invoice_lines.items) == 0


@pytest.mark.asyncio
async def test_remove_invoice_line_recalculates_totals() -> None:
    tenant_id = uuid4()
    unit_of_work = FakeBillingUnitOfWork()

    create_invoice = CreateInvoiceUseCase(unit_of_work)
    add_line = AddInvoiceLineUseCase(unit_of_work)
    remove_line = RemoveInvoiceLineUseCase(unit_of_work)

    invoice = await create_invoice.execute(
        tenant_id=tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=tenant_id),
        invoice_number="INV-0001",
        currency="USD",
        tax_amount=Decimal("5.00"),
    )

    first_line = await add_line.execute(
        tenant_id=tenant_id,
        invoice_id=invoice.id,
        description="First service",
        quantity=Decimal("2.0000"),
        unit_price=Decimal("10.00"),
    )

    await add_line.execute(
        tenant_id=tenant_id,
        invoice_id=invoice.id,
        description="Second service",
        quantity=Decimal("3.0000"),
        unit_price=Decimal("5.00"),
    )

    assert invoice.subtotal == Decimal("35.00")
    assert invoice.total_amount == Decimal("40.00")

    await remove_line.execute(
        tenant_id=tenant_id,
        invoice_id=invoice.id,
        invoice_line_id=first_line.id,
    )

    assert invoice.subtotal == Decimal("15.00")
    assert invoice.total_amount == Decimal("20.00")
    assert len(unit_of_work.fake_invoice_lines.items) == 1


@pytest.mark.asyncio
async def test_remove_invoice_line_rejects_non_draft_invoice() -> None:
    tenant_id = uuid4()
    unit_of_work = FakeBillingUnitOfWork()

    create_invoice = CreateInvoiceUseCase(unit_of_work)
    add_line = AddInvoiceLineUseCase(unit_of_work)
    remove_line = RemoveInvoiceLineUseCase(unit_of_work)

    invoice = await create_invoice.execute(
        tenant_id=tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=tenant_id),
        invoice_number="INV-0001",
        currency="USD",
    )

    invoice_line = await add_line.execute(
        tenant_id=tenant_id,
        invoice_id=invoice.id,
        description="Shipping service",
        quantity=Decimal("1.0000"),
        unit_price=Decimal("10.00"),
    )

    invoice.status = InvoiceStatus.ISSUED

    with pytest.raises(InvoiceNotEditableError):
        await remove_line.execute(
            tenant_id=tenant_id,
            invoice_id=invoice.id,
            invoice_line_id=invoice_line.id,
        )


@pytest.mark.asyncio
async def test_issue_invoice() -> None:
    tenant_id = uuid4()
    actor_id = uuid4()

    unit_of_work = FakeBillingUnitOfWork()
    add_invoice_ledger_accounts(
        unit_of_work,
        tenant_id=tenant_id,
    )

    create_invoice = CreateInvoiceUseCase(unit_of_work)
    add_line = AddInvoiceLineUseCase(unit_of_work)
    issue_invoice = IssueInvoiceUseCase(unit_of_work)

    invoice = await create_invoice.execute(
        tenant_id=tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=tenant_id),
        invoice_number="INV-0001",
        currency="USD",
    )

    await add_line.execute(
        tenant_id=tenant_id,
        invoice_id=invoice.id,
        description="Shipping service",
        quantity=Decimal("1.0000"),
        unit_price=Decimal("25.00"),
    )

    result = await issue_invoice.execute(
        tenant_id=tenant_id,
        invoice_id=invoice.id,
        actor_id=actor_id,
    )

    assert result.status == InvoiceStatus.ISSUED
    assert result.issued_at is not None


@pytest.mark.asyncio
async def test_issue_invoice_rejects_invoice_without_lines() -> None:
    tenant_id = uuid4()
    actor_id = uuid4()

    unit_of_work = FakeBillingUnitOfWork()

    create_invoice = CreateInvoiceUseCase(unit_of_work)
    issue_invoice = IssueInvoiceUseCase(unit_of_work)

    invoice = await create_invoice.execute(
        tenant_id=tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=tenant_id),
        invoice_number="INV-0001",
        currency="USD",
    )

    with pytest.raises(InvoiceHasNoLinesError):
        await issue_invoice.execute(
            tenant_id=tenant_id,
            invoice_id=invoice.id,
            actor_id=actor_id,
        )


@pytest.mark.asyncio
async def test_draft_invoice_can_be_voided() -> None:
    tenant_id = uuid4()
    actor_id = uuid4()

    unit_of_work = FakeBillingUnitOfWork()

    create_invoice = CreateInvoiceUseCase(unit_of_work)
    void_invoice = VoidInvoiceUseCase(unit_of_work)

    invoice = await create_invoice.execute(
        tenant_id=tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=tenant_id),
        invoice_number="INV-0001",
        currency="USD",
    )

    unit_of_work.committed = False

    result = await void_invoice.execute(
        tenant_id=tenant_id,
        invoice_id=invoice.id,
        actor_id=actor_id,
    )

    assert result.status == InvoiceStatus.VOID

    assert len(unit_of_work.fake_audit_logs.items) == 1

    audit_log = unit_of_work.fake_audit_logs.items[0]

    assert audit_log.tenant_id == tenant_id
    assert audit_log.actor_type == AuditActorType.USER
    assert audit_log.actor_id == actor_id

    assert audit_log.action == "invoice.voided"
    assert audit_log.resource_type == "invoice"
    assert audit_log.resource_id == invoice.id
    assert audit_log.outcome == AuditOutcome.SUCCESS

    assert audit_log.metadata_ == {
        "invoice_number": "INV-0001",
        "customer_id": str(invoice.customer_id),
        "currency": "USD",
        "subtotal": "0.00",
        "tax_amount": "0.00",
        "total_amount": "0.00",
    }

    assert unit_of_work.committed is True


@pytest.mark.asyncio
async def test_paid_invoice_cannot_be_voided() -> None:
    tenant_id = uuid4()
    issue_actor_id = uuid4()
    void_actor_id = uuid4()

    unit_of_work = FakeBillingUnitOfWork()

    add_invoice_ledger_accounts(
        unit_of_work,
        tenant_id=tenant_id,
    )

    create_invoice = CreateInvoiceUseCase(unit_of_work)
    add_line = AddInvoiceLineUseCase(unit_of_work)
    issue_invoice = IssueInvoiceUseCase(unit_of_work)
    void_invoice = VoidInvoiceUseCase(unit_of_work)

    invoice = await create_invoice.execute(
        tenant_id=tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=tenant_id),
        invoice_number="INV-0001",
        currency="USD",
    )

    await add_line.execute(
        tenant_id=tenant_id,
        invoice_id=invoice.id,
        description="Shipping service",
        quantity=Decimal("1.0000"),
        unit_price=Decimal("25.00"),
    )

    await issue_invoice.execute(
        tenant_id=tenant_id,
        invoice_id=invoice.id,
        actor_id=issue_actor_id,
    )

    invoice.status = InvoiceStatus.PAID

    audit_count_before_void = len(unit_of_work.fake_audit_logs.items)

    unit_of_work.committed = False

    with pytest.raises(InvalidInvoiceStateTransitionError):
        await void_invoice.execute(
            tenant_id=tenant_id,
            invoice_id=invoice.id,
            actor_id=void_actor_id,
        )

    assert invoice.status == InvoiceStatus.PAID

    assert len(unit_of_work.fake_audit_logs.items) == audit_count_before_void

    assert all(
        audit_log.action != "invoice.voided" for audit_log in unit_of_work.fake_audit_logs.items
    )

    assert unit_of_work.committed is False


@pytest.mark.asyncio
async def test_get_invoice() -> None:
    tenant_id = uuid4()
    unit_of_work = FakeBillingUnitOfWork()

    create_invoice = CreateInvoiceUseCase(unit_of_work)
    get_invoice = GetInvoiceUseCase(unit_of_work)

    created_invoice = await create_invoice.execute(
        tenant_id=tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=tenant_id),
        invoice_number="INV-0001",
        currency="USD",
    )

    invoice = await get_invoice.execute(
        tenant_id=tenant_id,
        invoice_id=created_invoice.id,
    )

    assert invoice.id == created_invoice.id
    assert invoice.invoice_number == "INV-0001"


@pytest.mark.asyncio
async def test_get_invoice_rejects_foreign_tenant() -> None:
    owner_tenant_id = uuid4()
    foreign_tenant_id = uuid4()

    unit_of_work = FakeBillingUnitOfWork()

    create_invoice = CreateInvoiceUseCase(unit_of_work)
    get_invoice = GetInvoiceUseCase(unit_of_work)

    invoice = await create_invoice.execute(
        tenant_id=owner_tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=owner_tenant_id),
        invoice_number="INV-0001",
        currency="USD",
    )

    with pytest.raises(InvoiceNotFoundError):
        await get_invoice.execute(
            tenant_id=foreign_tenant_id,
            invoice_id=invoice.id,
        )


@pytest.mark.asyncio
async def test_list_invoices_only_returns_current_tenant() -> None:
    first_tenant_id = uuid4()
    second_tenant_id = uuid4()

    unit_of_work = FakeBillingUnitOfWork()
    create_invoice = CreateInvoiceUseCase(unit_of_work)
    list_invoices = ListInvoicesUseCase(unit_of_work)

    await create_invoice.execute(
        tenant_id=first_tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=first_tenant_id),
        invoice_number="INV-0001",
        currency="USD",
    )

    await create_invoice.execute(
        tenant_id=first_tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=first_tenant_id),
        invoice_number="INV-0002",
        currency="USD",
    )

    await create_invoice.execute(
        tenant_id=second_tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=second_tenant_id),
        invoice_number="INV-0001",
        currency="USD",
    )

    invoices = await list_invoices.execute(
        tenant_id=first_tenant_id,
    )

    assert len(invoices) == 2
    assert all(invoice.tenant_id == first_tenant_id for invoice in invoices)


@pytest.mark.asyncio
async def test_remove_invoice_line_rejects_foreign_tenant() -> None:
    owner_tenant_id = uuid4()
    foreign_tenant_id = uuid4()

    unit_of_work = FakeBillingUnitOfWork()

    create_invoice = CreateInvoiceUseCase(unit_of_work)
    add_line = AddInvoiceLineUseCase(unit_of_work)
    remove_line = RemoveInvoiceLineUseCase(unit_of_work)

    invoice = await create_invoice.execute(
        tenant_id=owner_tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=owner_tenant_id),
        invoice_number="INV-0001",
        currency="USD",
    )

    invoice_line = await add_line.execute(
        tenant_id=owner_tenant_id,
        invoice_id=invoice.id,
        description="Shipping service",
        quantity=Decimal("1.0000"),
        unit_price=Decimal("25.00"),
    )

    with pytest.raises(InvoiceNotFoundError):
        await remove_line.execute(
            tenant_id=foreign_tenant_id,
            invoice_id=invoice.id,
            invoice_line_id=invoice_line.id,
        )


@pytest.mark.asyncio
async def test_remove_invoice_line_rejects_line_from_another_invoice() -> None:
    tenant_id = uuid4()

    unit_of_work = FakeBillingUnitOfWork()

    create_invoice = CreateInvoiceUseCase(unit_of_work)
    add_line = AddInvoiceLineUseCase(unit_of_work)
    remove_line = RemoveInvoiceLineUseCase(unit_of_work)

    first_invoice = await create_invoice.execute(
        tenant_id=tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=tenant_id),
        invoice_number="INV-0001",
        currency="USD",
    )

    second_invoice = await create_invoice.execute(
        tenant_id=tenant_id,
        customer_id=add_customer(unit_of_work, tenant_id=tenant_id),
        invoice_number="INV-0002",
        currency="USD",
    )

    second_invoice_line = await add_line.execute(
        tenant_id=tenant_id,
        invoice_id=second_invoice.id,
        description="Second invoice service",
        quantity=Decimal("1.0000"),
        unit_price=Decimal("25.00"),
    )

    with pytest.raises(InvoiceLineNotFoundError):
        await remove_line.execute(
            tenant_id=tenant_id,
            invoice_id=first_invoice.id,
            invoice_line_id=second_invoice_line.id,
        )
