from app.modules.billing.domain.enums import InvoiceStatus

_ALLOWED_TRANSITIONS: dict[
    InvoiceStatus,
    set[InvoiceStatus],
] = {
    InvoiceStatus.DRAFT: {
        InvoiceStatus.ISSUED,
        InvoiceStatus.VOID,
    },
    InvoiceStatus.ISSUED: {
        InvoiceStatus.PAID,
        InvoiceStatus.VOID,
    },
    InvoiceStatus.PAID: set(),
    InvoiceStatus.VOID: set(),
}


def can_transition_invoice_status(
    current_status: InvoiceStatus,
    target_status: InvoiceStatus,
) -> bool:
    return target_status in _ALLOWED_TRANSITIONS[current_status]
