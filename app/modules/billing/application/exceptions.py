class BillingError(Exception):
    """Base exception for billing application errors."""


class InvoiceNotFoundError(BillingError):
    pass


class InvoiceLineNotFoundError(BillingError):
    pass


class InvoiceNumberAlreadyExistsError(BillingError):
    pass


class InvalidInvoiceStateTransitionError(BillingError):
    pass


class InvoiceNotEditableError(BillingError):
    pass


class InvoiceHasNoLinesError(BillingError):
    pass


class InvalidInvoiceAmountError(BillingError):
    pass


class CustomerNotFoundError(BillingError):
    pass


class ShipmentNotFoundError(BillingError):
    pass
