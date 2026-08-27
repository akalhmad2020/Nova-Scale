class ShipmentEventError(Exception):
    """Base exception for shipment event application errors."""


class ShipmentEventShipmentNotFoundError(ShipmentEventError):
    """Raised when a shipment is not valid for the tenant."""


class ShipmentEventLocationNotFoundError(ShipmentEventError):
    """Raised when an event location is not valid for the tenant."""
