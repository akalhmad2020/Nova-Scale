from enum import StrEnum


class NotificationChannel(StrEnum):
    EMAIL = "email"
    WEBHOOK = "webhook"


class NotificationStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class NotificationAttemptStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
