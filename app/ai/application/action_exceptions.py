class AgentActionError(Exception):
    """Base exception for persisted AI actions."""


class AgentActionNotFoundError(AgentActionError):
    """Raised when an AI action cannot be found for the current owner."""


class AgentActionConflictError(AgentActionError):
    """Raised when an AI action cannot be changed from its current state."""


class AgentActionInProgressError(AgentActionConflictError):
    """Raised when an AI action is already being executed."""


class PendingAgentActionExistsError(AgentActionConflictError):
    """Raised when a conversation already has an active AI action."""


class AgentActionPermissionDeniedError(AgentActionError):
    """Raised when current permissions do not allow confirming an AI action."""


class AgentActionExecutionError(AgentActionError):
    """Raised when a confirmed AI action cannot be executed safely."""


class AgentActionProposalRejectedError(AgentActionError):
    """Raised when a requested write action is invalid or has no effect."""
