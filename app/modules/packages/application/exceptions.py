class PackageError(Exception):
    """Base exception for package application errors."""


class PackageNotFoundError(PackageError):
    """Raised when a package cannot be found."""


class PackageNumberAlreadyExistsError(PackageError):
    """Raised when a package number already exists in the shipment."""


class PackageShipmentNotFoundError(PackageError):
    """Raised when the shipment is invalid for the tenant."""
