from uuid import UUID

from app.modules.audit.domain.enums import AuditActorType


def validate_audit_actor(
    *,
    actor_type: AuditActorType,
    actor_id: UUID | None,
) -> None:
    if actor_type is AuditActorType.USER and actor_id is None:
        raise ValueError("User audit actor must have an actor ID.")

    if actor_type is AuditActorType.SYSTEM and actor_id is not None:
        raise ValueError("System audit actor must not have an actor ID.")


def validate_audit_action(action: str) -> str:
    normalized = action.strip()

    if not normalized:
        raise ValueError("Audit action must not be empty.")

    if len(normalized) > 100:
        raise ValueError("Audit action must not exceed 100 characters.")

    return normalized


def validate_audit_resource_type(resource_type: str) -> str:
    normalized = resource_type.strip()

    if not normalized:
        raise ValueError("Audit resource type must not be empty.")

    if len(normalized) > 100:
        raise ValueError("Audit resource type must not exceed 100 characters.")

    return normalized
