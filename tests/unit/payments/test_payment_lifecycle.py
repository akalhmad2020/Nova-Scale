from app.modules.payments.domain.enums import PaymentStatus
from app.modules.payments.domain.lifecycle import can_transition_payment_status


def test_draft_payment_can_be_posted() -> None:
    assert can_transition_payment_status(
        PaymentStatus.DRAFT,
        PaymentStatus.POSTED,
    )


def test_draft_payment_can_be_voided() -> None:
    assert can_transition_payment_status(
        PaymentStatus.DRAFT,
        PaymentStatus.VOID,
    )


def test_posted_payment_is_terminal() -> None:
    assert not can_transition_payment_status(
        PaymentStatus.POSTED,
        PaymentStatus.DRAFT,
    )
    assert not can_transition_payment_status(
        PaymentStatus.POSTED,
        PaymentStatus.VOID,
    )


def test_void_payment_is_terminal() -> None:
    assert not can_transition_payment_status(
        PaymentStatus.VOID,
        PaymentStatus.DRAFT,
    )
    assert not can_transition_payment_status(
        PaymentStatus.VOID,
        PaymentStatus.POSTED,
    )
