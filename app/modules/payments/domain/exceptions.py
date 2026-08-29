class PaymentNotFoundError(Exception):
    pass


class DuplicatePaymentNumberError(Exception):
    pass


class PaymentCustomerNotFoundError(Exception):
    pass


class PaymentAllocationNotFoundError(Exception):
    pass


class DuplicatePaymentAllocationError(Exception):
    pass


class InvalidPaymentStateTransitionError(Exception):
    pass


class PaymentAllocationExceedsPaymentError(Exception):
    pass


class PaymentAllocationExceedsInvoiceError(Exception):
    pass


class PaymentCurrencyMismatchError(Exception):
    pass


class InvalidInvoiceForPaymentError(Exception):
    pass
