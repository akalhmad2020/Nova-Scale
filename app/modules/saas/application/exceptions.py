class SubscriptionNotFoundError(Exception):
    """Raised when a tenant subscription cannot be found."""


class InvalidSubscriptionTransitionError(Exception):
    """Raised when a requested subscription lifecycle transition is invalid."""
