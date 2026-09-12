class AIRequestLimitError(ValueError):
    pass


class AIResponseLimitError(RuntimeError):
    pass


class AIProviderUnavailableError(RuntimeError):
    """Raised when the configured AI provider is temporarily unavailable."""

    pass
