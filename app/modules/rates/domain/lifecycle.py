from app.modules.rates.domain.enums import RateQuoteStatus

ALLOWED_RATE_QUOTE_TRANSITIONS: dict[
    RateQuoteStatus,
    set[RateQuoteStatus],
] = {
    RateQuoteStatus.DRAFT: {
        RateQuoteStatus.QUOTED,
        RateQuoteStatus.CANCELLED,
    },
    RateQuoteStatus.QUOTED: {
        RateQuoteStatus.ACCEPTED,
        RateQuoteStatus.EXPIRED,
        RateQuoteStatus.CANCELLED,
    },
    RateQuoteStatus.ACCEPTED: set(),
    RateQuoteStatus.EXPIRED: set(),
    RateQuoteStatus.CANCELLED: set(),
}


def can_transition_rate_quote_status(
    current_status: RateQuoteStatus,
    target_status: RateQuoteStatus,
) -> bool:
    return target_status in ALLOWED_RATE_QUOTE_TRANSITIONS[current_status]
