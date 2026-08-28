from app.core.database import SessionFactory
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
from app.modules.billing.application.use_cases.mark_invoice_paid import (
    MarkInvoicePaidUseCase,
)
from app.modules.billing.application.use_cases.remove_invoice_line import (
    RemoveInvoiceLineUseCase,
)
from app.modules.billing.application.use_cases.void_invoice import (
    VoidInvoiceUseCase,
)
from app.modules.billing.infrastructure.unit_of_work import (
    SQLAlchemyBillingUnitOfWork,
)


def get_create_invoice_use_case() -> CreateInvoiceUseCase:
    return CreateInvoiceUseCase(
        unit_of_work=SQLAlchemyBillingUnitOfWork(SessionFactory),
    )


def get_get_invoice_use_case() -> GetInvoiceUseCase:
    return GetInvoiceUseCase(
        unit_of_work=SQLAlchemyBillingUnitOfWork(SessionFactory),
    )


def get_list_invoices_use_case() -> ListInvoicesUseCase:
    return ListInvoicesUseCase(
        unit_of_work=SQLAlchemyBillingUnitOfWork(SessionFactory),
    )


def get_add_invoice_line_use_case() -> AddInvoiceLineUseCase:
    return AddInvoiceLineUseCase(
        unit_of_work=SQLAlchemyBillingUnitOfWork(SessionFactory),
    )


def get_remove_invoice_line_use_case() -> RemoveInvoiceLineUseCase:
    return RemoveInvoiceLineUseCase(
        unit_of_work=SQLAlchemyBillingUnitOfWork(SessionFactory),
    )


def get_issue_invoice_use_case() -> IssueInvoiceUseCase:
    return IssueInvoiceUseCase(
        unit_of_work=SQLAlchemyBillingUnitOfWork(SessionFactory),
    )


def get_mark_invoice_paid_use_case() -> MarkInvoicePaidUseCase:
    return MarkInvoicePaidUseCase(
        unit_of_work=SQLAlchemyBillingUnitOfWork(SessionFactory),
    )


def get_void_invoice_use_case() -> VoidInvoiceUseCase:
    return VoidInvoiceUseCase(
        unit_of_work=SQLAlchemyBillingUnitOfWork(SessionFactory),
    )
