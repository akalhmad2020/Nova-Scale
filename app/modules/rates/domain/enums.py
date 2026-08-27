from enum import StrEnum


class RateQuoteStatus(StrEnum):
    DRAFT = "draft"
    QUOTED = "quoted"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
