class EntitlementDeniedError(Exception):
    """Raised when the current plan does not grant a requested capability."""


class EntitlementLimitExceededError(Exception):
    """Raised when a plan usage limit would be exceeded."""
