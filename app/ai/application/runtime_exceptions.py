class AIRequestLimitError(ValueError):
    """Raised when an AI request exceeds a configured runtime budget."""


class AIResponseLimitError(RuntimeError):
    """Raised when an AI provider returns a response beyond the configured budget."""
