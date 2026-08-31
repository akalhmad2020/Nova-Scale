from enum import StrEnum


class LedgerAccountType(StrEnum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


class LedgerAccountPurpose(StrEnum):
    ACCOUNTS_RECEIVABLE = "accounts_receivable"
    REVENUE = "revenue"
    CASH = "cash"
    TAX_PAYABLE = "tax_payable"


class LedgerAccountStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class JournalSourceType(StrEnum):
    INVOICE_ISSUED = "invoice_issued"
    INVOICE_VOIDED = "invoice_voided"
    PAYMENT_POSTED = "payment_posted"
