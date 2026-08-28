from enum import StrEnum


class DocumentType(StrEnum):
    SHIPPING_LABEL = "shipping_label"
    COMMERCIAL_INVOICE = "commercial_invoice"
    PACKING_SLIP = "packing_slip"
    OTHER = "other"


class DocumentStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class LabelStatus(StrEnum):
    PENDING = "pending"
    GENERATED = "generated"
    VOIDED = "voided"
    FAILED = "failed"
