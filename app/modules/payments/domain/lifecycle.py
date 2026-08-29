from app.modules.payments.domain.enums import PaymentStatus

_ALLOWED_TRANSITIONS: dict[PaymentStatus, set[PaymentStatus]] = {
    PaymentStatus.DRAFT: {
        PaymentStatus.POSTED,
        PaymentStatus.VOID,
    },
    PaymentStatus.POSTED: set(),
    PaymentStatus.VOID: set(),
}


def can_transition_payment_status(
    current_status: PaymentStatus,
    target_status: PaymentStatus,
) -> bool:
    return target_status in _ALLOWED_TRANSITIONS[current_status]
