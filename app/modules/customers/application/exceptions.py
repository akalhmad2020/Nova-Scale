class CustomerError(Exception):
    """Base exception for customer application errors."""


class CustomerCodeAlreadyExistsError(CustomerError):
    """Raised when a customer code already exists in the tenant."""


class CustomerNotFoundError(CustomerError):
    """Raised when a customer cannot be found."""
