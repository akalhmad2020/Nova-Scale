from enum import StrEnum


class PaymentStatus(StrEnum):
    DRAFT = "draft"
    POSTED = "posted"
    VOID = "void"


class PaymentMethod(StrEnum):
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"
    CARD = "card"
    CHECK = "check"
    OTHER = "other"
