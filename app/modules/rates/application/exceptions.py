class RateQuoteError(Exception):
    """Base exception for rate quote application errors."""


class RateQuoteNotFoundError(RateQuoteError):
    """Raised when a rate quote cannot be found."""


class RateQuoteShipmentNotFoundError(RateQuoteError):
    """Raised when the shipment is invalid for the tenant."""


class InvalidRateQuoteStatusTransitionError(RateQuoteError):
    """Raised when a rate quote status transition is invalid."""
