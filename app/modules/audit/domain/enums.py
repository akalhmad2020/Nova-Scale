from enum import StrEnum


class AuditActorType(StrEnum):
    USER = "user"
    SYSTEM = "system"


class AuditOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
