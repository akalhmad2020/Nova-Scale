from contextvars import ContextVar, Token
from uuid import UUID

_current_tenant_id: ContextVar[UUID | None] = ContextVar(
    "current_tenant_id",
    default=None,
)


def get_current_tenant_id() -> UUID | None:
    return _current_tenant_id.get()


def set_current_tenant_id(tenant_id: UUID) -> Token[UUID | None]:
    return _current_tenant_id.set(tenant_id)


def reset_current_tenant_id(token: Token[UUID | None]) -> None:
    _current_tenant_id.reset(token)
