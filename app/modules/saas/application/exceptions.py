class SubscriptionNotFoundError(Exception):
    """Raised when a tenant subscription cannot be found."""


class InvalidSubscriptionTransitionError(Exception):
    """Raised when a requested subscription lifecycle transition is invalid."""


class SelfServicePlanUnavailableError(Exception):
    """Raised when a plan cannot be activated through self-service."""


class SubscriptionProviderUnavailableError(Exception):
    """Raised when the configured billing provider adapter is unavailable."""
