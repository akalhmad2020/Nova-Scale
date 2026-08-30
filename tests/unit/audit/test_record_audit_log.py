from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.modules.audit.application.contracts import AuditRecord
from app.modules.audit.application.use_cases.record_audit_log import (
    RecordAuditLogUseCase,
)
from app.modules.audit.domain.enums import AuditActorType, AuditOutcome
from app.modules.audit.infrastructure.models.audit_log import AuditLog


class FakeAuditLogRepository:
    def __init__(self) -> None:
        self.items: list[AuditLog] = []

    async def add(self, audit_log: AuditLog) -> None:
        self.items.append(audit_log)

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        audit_log_id: UUID,
    ) -> AuditLog | None:
        for item in self.items:
            if item.tenant_id == tenant_id and item.id == audit_log_id:
                return item

        return None

    async def list_for_tenant(
        self,
        *,
        tenant_id: UUID,
        limit: int = 100,
        offset: int = 0,
        actor_id: UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> Sequence[AuditLog]:
        items = [item for item in self.items if item.tenant_id == tenant_id]

        if actor_id is not None:
            items = [item for item in items if item.actor_id == actor_id]

        if action is not None:
            items = [item for item in items if item.action == action]

        if resource_type is not None:
            items = [item for item in items if item.resource_type == resource_type]

        if resource_id is not None:
            items = [item for item in items if item.resource_id == resource_id]

        if occurred_from is not None:
            items = [item for item in items if item.occurred_at >= occurred_from]

        if occurred_to is not None:
            items = [item for item in items if item.occurred_at <= occurred_to]

        return items[offset : offset + limit]


@pytest.mark.asyncio
async def test_records_user_audit_log() -> None:
    repository = FakeAuditLogRepository()
    use_case = RecordAuditLogUseCase(repository)

    tenant_id = uuid4()
    actor_id = uuid4()
    resource_id = uuid4()
    occurred_at = datetime.now(UTC)

    result = await use_case.execute(
        AuditRecord(
            tenant_id=tenant_id,
            actor_type=AuditActorType.USER,
            actor_id=actor_id,
            action=" invoice.issue ",
            resource_type=" invoice ",
            resource_id=resource_id,
            outcome=AuditOutcome.SUCCESS,
            metadata={"invoice_number": "INV-001"},
            occurred_at=occurred_at,
        )
    )

    assert len(repository.items) == 1
    assert result is repository.items[0]

    assert result.tenant_id == tenant_id
    assert result.actor_type == AuditActorType.USER
    assert result.actor_id == actor_id
    assert result.action == "invoice.issue"
    assert result.resource_type == "invoice"
    assert result.resource_id == resource_id
    assert result.outcome == AuditOutcome.SUCCESS
    assert result.metadata_ == {"invoice_number": "INV-001"}
    assert result.occurred_at == occurred_at


@pytest.mark.asyncio
async def test_records_system_audit_log_without_actor_id() -> None:
    repository = FakeAuditLogRepository()
    use_case = RecordAuditLogUseCase(repository)

    result = await use_case.execute(
        AuditRecord(
            tenant_id=uuid4(),
            actor_type=AuditActorType.SYSTEM,
            actor_id=None,
            action="notification.deliver",
            resource_type="notification",
            resource_id=uuid4(),
        )
    )

    assert result.actor_type == AuditActorType.SYSTEM
    assert result.actor_id is None


@pytest.mark.asyncio
async def test_rejects_user_actor_without_actor_id() -> None:
    repository = FakeAuditLogRepository()
    use_case = RecordAuditLogUseCase(repository)

    with pytest.raises(
        ValueError,
        match="User audit actor must have an actor ID",
    ):
        await use_case.execute(
            AuditRecord(
                tenant_id=uuid4(),
                actor_type=AuditActorType.USER,
                actor_id=None,
                action="invoice.issue",
                resource_type="invoice",
                resource_id=uuid4(),
            )
        )

    assert repository.items == []


@pytest.mark.asyncio
async def test_rejects_system_actor_with_actor_id() -> None:
    repository = FakeAuditLogRepository()
    use_case = RecordAuditLogUseCase(repository)

    with pytest.raises(
        ValueError,
        match="System audit actor must not have an actor ID",
    ):
        await use_case.execute(
            AuditRecord(
                tenant_id=uuid4(),
                actor_type=AuditActorType.SYSTEM,
                actor_id=uuid4(),
                action="notification.deliver",
                resource_type="notification",
                resource_id=uuid4(),
            )
        )

    assert repository.items == []


@pytest.mark.asyncio
async def test_rejects_empty_action() -> None:
    repository = FakeAuditLogRepository()
    use_case = RecordAuditLogUseCase(repository)

    with pytest.raises(
        ValueError,
        match="Audit action must not be empty",
    ):
        await use_case.execute(
            AuditRecord(
                tenant_id=uuid4(),
                actor_type=AuditActorType.SYSTEM,
                actor_id=None,
                action="   ",
                resource_type="invoice",
                resource_id=uuid4(),
            )
        )

    assert repository.items == []


@pytest.mark.asyncio
async def test_rejects_empty_resource_type() -> None:
    repository = FakeAuditLogRepository()
    use_case = RecordAuditLogUseCase(repository)

    with pytest.raises(
        ValueError,
        match="Audit resource type must not be empty",
    ):
        await use_case.execute(
            AuditRecord(
                tenant_id=uuid4(),
                actor_type=AuditActorType.SYSTEM,
                actor_id=None,
                action="invoice.issue",
                resource_type="   ",
                resource_id=uuid4(),
            )
        )

    assert repository.items == []
