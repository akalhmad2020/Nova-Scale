from app.modules.billing.domain.enums import InvoiceStatus
from app.modules.billing.domain.lifecycle import (
    can_transition_invoice_status,
)


def test_draft_invoice_can_be_issued() -> None:
    assert can_transition_invoice_status(
        InvoiceStatus.DRAFT,
        InvoiceStatus.ISSUED,
    )


def test_draft_invoice_can_be_voided() -> None:
    assert can_transition_invoice_status(
        InvoiceStatus.DRAFT,
        InvoiceStatus.VOID,
    )


def test_issued_invoice_can_be_paid() -> None:
    assert can_transition_invoice_status(
        InvoiceStatus.ISSUED,
        InvoiceStatus.PAID,
    )


def test_issued_invoice_can_be_voided() -> None:
    assert can_transition_invoice_status(
        InvoiceStatus.ISSUED,
        InvoiceStatus.VOID,
    )


def test_draft_invoice_cannot_be_paid() -> None:
    assert not can_transition_invoice_status(
        InvoiceStatus.DRAFT,
        InvoiceStatus.PAID,
    )


def test_paid_invoice_is_terminal() -> None:
    for target_status in InvoiceStatus:
        assert not can_transition_invoice_status(
            InvoiceStatus.PAID,
            target_status,
        )


def test_void_invoice_is_terminal() -> None:
    for target_status in InvoiceStatus:
        assert not can_transition_invoice_status(
            InvoiceStatus.VOID,
            target_status,
        )
