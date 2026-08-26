class ShipmentError(Exception):
    """Base exception for shipment application errors."""


class ShipmentTrackingNumberAlreadyExistsError(ShipmentError):
    """Raised when a tracking number already exists in the tenant."""


class ShipmentCustomerNotFoundError(ShipmentError):
    """Raised when the shipment customer is invalid for the tenant."""


class ShipmentOriginLocationNotFoundError(ShipmentError):
    """Raised when the origin location is invalid for the tenant."""


class ShipmentDestinationLocationNotFoundError(ShipmentError):
    """Raised when the destination location is invalid for the tenant."""


class ShipmentNotFoundError(ShipmentError):
    """Raised when a shipment cannot be found."""


class InvalidShipmentStatusTransitionError(ShipmentError):
    """Raised when a shipment status transition is not allowed."""
