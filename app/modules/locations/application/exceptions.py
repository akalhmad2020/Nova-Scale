class LocationError(Exception):
    """Base exception for location application errors."""


class LocationCodeAlreadyExistsError(LocationError):
    """Raised when a location code already exists in the tenant."""


class LocationNotFoundError(LocationError):
    """Raised when a location cannot be found."""
