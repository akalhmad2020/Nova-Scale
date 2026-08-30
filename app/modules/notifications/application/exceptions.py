class NotificationError(Exception):
    pass


class NotificationNotFoundError(NotificationError):
    pass


class NotificationAlreadyProcessedError(NotificationError):
    pass


class NotificationNotReadyError(NotificationError):
    pass


class NotificationProviderNotConfiguredError(NotificationError):
    pass


class NotificationIdempotencyConflictError(NotificationError):
    pass


class NotificationDeliveryError(NotificationError):
    pass
