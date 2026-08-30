from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.domain.enums import AuditActorType, AuditOutcome
from app.modules.audit.infrastructure.models.audit_log import AuditLog
from app.modules.audit.infrastructure.repositories.sqlalchemy import (
    SQLAlchemyAuditLogRepository,
)


@pytest.mark.integration
async def test_audit_repository_adds_and_reads_audit_log(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyAuditLogRepository(db_session)

    tenant_id = uuid4()
    actor_id = uuid4()
    resource_id = uuid4()

    audit_log = AuditLog(
        tenant_id=tenant_id,
        actor_type=AuditActorType.USER,
        actor_id=actor_id,
        action="payment.created",
        resource_type="payment",
        resource_id=resource_id,
        outcome=AuditOutcome.SUCCESS,
        metadata_={"source": "integration-test"},
        occurred_at=datetime.now(UTC),
    )

    await repository.add(audit_log)

    assert audit_log.id is not None

    stored_audit_log = await repository.get_by_id(
        tenant_id=tenant_id,
        audit_log_id=audit_log.id,
    )

    assert stored_audit_log is not None
    assert stored_audit_log.id == audit_log.id
    assert stored_audit_log.tenant_id == tenant_id
    assert stored_audit_log.actor_type == AuditActorType.USER
    assert stored_audit_log.actor_id == actor_id
    assert stored_audit_log.action == "payment.created"
    assert stored_audit_log.resource_type == "payment"
    assert stored_audit_log.resource_id == resource_id
    assert stored_audit_log.outcome == AuditOutcome.SUCCESS
    assert stored_audit_log.metadata_ == {"source": "integration-test"}


@pytest.mark.integration
async def test_audit_repository_get_by_id_is_tenant_scoped(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyAuditLogRepository(db_session)

    tenant_id = uuid4()
    other_tenant_id = uuid4()

    audit_log = AuditLog(
        tenant_id=tenant_id,
        actor_type=AuditActorType.SYSTEM,
        actor_id=None,
        action="invoice.issued",
        resource_type="invoice",
        resource_id=uuid4(),
        outcome=AuditOutcome.SUCCESS,
        metadata_={},
        occurred_at=datetime.now(UTC),
    )

    await repository.add(audit_log)

    stored_audit_log = await repository.get_by_id(
        tenant_id=other_tenant_id,
        audit_log_id=audit_log.id,
    )

    assert stored_audit_log is None


@pytest.mark.integration
async def test_audit_repository_lists_only_requested_tenant(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyAuditLogRepository(db_session)

    tenant_id = uuid4()
    other_tenant_id = uuid4()

    first_log = AuditLog(
        tenant_id=tenant_id,
        actor_type=AuditActorType.SYSTEM,
        actor_id=None,
        action="shipment.created",
        resource_type="shipment",
        resource_id=uuid4(),
        outcome=AuditOutcome.SUCCESS,
        metadata_={},
        occurred_at=datetime.now(UTC) - timedelta(minutes=2),
    )

    second_log = AuditLog(
        tenant_id=tenant_id,
        actor_type=AuditActorType.SYSTEM,
        actor_id=None,
        action="shipment.updated",
        resource_type="shipment",
        resource_id=uuid4(),
        outcome=AuditOutcome.SUCCESS,
        metadata_={},
        occurred_at=datetime.now(UTC) - timedelta(minutes=1),
    )

    other_tenant_log = AuditLog(
        tenant_id=other_tenant_id,
        actor_type=AuditActorType.SYSTEM,
        actor_id=None,
        action="shipment.created",
        resource_type="shipment",
        resource_id=uuid4(),
        outcome=AuditOutcome.SUCCESS,
        metadata_={},
        occurred_at=datetime.now(UTC),
    )

    await repository.add(first_log)
    await repository.add(second_log)
    await repository.add(other_tenant_log)

    results = await repository.list_for_tenant(
        tenant_id=tenant_id,
    )

    result_ids = {audit_log.id for audit_log in results}

    assert first_log.id in result_ids
    assert second_log.id in result_ids
    assert other_tenant_log.id not in result_ids


@pytest.mark.integration
async def test_audit_repository_filters_by_actor_and_action(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyAuditLogRepository(db_session)

    tenant_id = uuid4()
    actor_id = uuid4()
    other_actor_id = uuid4()

    matching_log = AuditLog(
        tenant_id=tenant_id,
        actor_type=AuditActorType.USER,
        actor_id=actor_id,
        action="payment.posted",
        resource_type="payment",
        resource_id=uuid4(),
        outcome=AuditOutcome.SUCCESS,
        metadata_={},
        occurred_at=datetime.now(UTC),
    )

    different_actor_log = AuditLog(
        tenant_id=tenant_id,
        actor_type=AuditActorType.USER,
        actor_id=other_actor_id,
        action="payment.posted",
        resource_type="payment",
        resource_id=uuid4(),
        outcome=AuditOutcome.SUCCESS,
        metadata_={},
        occurred_at=datetime.now(UTC),
    )

    different_action_log = AuditLog(
        tenant_id=tenant_id,
        actor_type=AuditActorType.USER,
        actor_id=actor_id,
        action="payment.voided",
        resource_type="payment",
        resource_id=uuid4(),
        outcome=AuditOutcome.SUCCESS,
        metadata_={},
        occurred_at=datetime.now(UTC),
    )

    await repository.add(matching_log)
    await repository.add(different_actor_log)
    await repository.add(different_action_log)

    results = await repository.list_for_tenant(
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="payment.posted",
    )

    assert [audit_log.id for audit_log in results] == [matching_log.id]


@pytest.mark.integration
async def test_audit_repository_filters_by_resource(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyAuditLogRepository(db_session)

    tenant_id = uuid4()
    resource_id = uuid4()

    matching_log = AuditLog(
        tenant_id=tenant_id,
        actor_type=AuditActorType.SYSTEM,
        actor_id=None,
        action="shipment.transitioned",
        resource_type="shipment",
        resource_id=resource_id,
        outcome=AuditOutcome.SUCCESS,
        metadata_={},
        occurred_at=datetime.now(UTC),
    )

    other_resource_log = AuditLog(
        tenant_id=tenant_id,
        actor_type=AuditActorType.SYSTEM,
        actor_id=None,
        action="shipment.transitioned",
        resource_type="shipment",
        resource_id=uuid4(),
        outcome=AuditOutcome.SUCCESS,
        metadata_={},
        occurred_at=datetime.now(UTC),
    )

    await repository.add(matching_log)
    await repository.add(other_resource_log)

    results = await repository.list_for_tenant(
        tenant_id=tenant_id,
        resource_type="shipment",
        resource_id=resource_id,
    )

    assert [audit_log.id for audit_log in results] == [matching_log.id]


@pytest.mark.integration
async def test_audit_repository_filters_by_occurred_at_range(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyAuditLogRepository(db_session)

    tenant_id = uuid4()
    now = datetime.now(UTC)

    older_log = AuditLog(
        tenant_id=tenant_id,
        actor_type=AuditActorType.SYSTEM,
        actor_id=None,
        action="system.started",
        resource_type="system",
        resource_id=None,
        outcome=AuditOutcome.SUCCESS,
        metadata_={},
        occurred_at=now - timedelta(hours=2),
    )

    matching_log = AuditLog(
        tenant_id=tenant_id,
        actor_type=AuditActorType.SYSTEM,
        actor_id=None,
        action="system.checked",
        resource_type="system",
        resource_id=None,
        outcome=AuditOutcome.SUCCESS,
        metadata_={},
        occurred_at=now,
    )

    newer_log = AuditLog(
        tenant_id=tenant_id,
        actor_type=AuditActorType.SYSTEM,
        actor_id=None,
        action="system.finished",
        resource_type="system",
        resource_id=None,
        outcome=AuditOutcome.SUCCESS,
        metadata_={},
        occurred_at=now + timedelta(hours=2),
    )

    await repository.add(older_log)
    await repository.add(matching_log)
    await repository.add(newer_log)

    results = await repository.list_for_tenant(
        tenant_id=tenant_id,
        occurred_from=now - timedelta(minutes=30),
        occurred_to=now + timedelta(minutes=30),
    )

    assert [audit_log.id for audit_log in results] == [matching_log.id]


@pytest.mark.integration
async def test_audit_repository_orders_newest_first(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyAuditLogRepository(db_session)

    tenant_id = uuid4()
    now = datetime.now(UTC)

    older_log = AuditLog(
        tenant_id=tenant_id,
        actor_type=AuditActorType.SYSTEM,
        actor_id=None,
        action="shipment.created",
        resource_type="shipment",
        resource_id=uuid4(),
        outcome=AuditOutcome.SUCCESS,
        metadata_={},
        occurred_at=now - timedelta(minutes=2),
    )

    newer_log = AuditLog(
        tenant_id=tenant_id,
        actor_type=AuditActorType.SYSTEM,
        actor_id=None,
        action="shipment.updated",
        resource_type="shipment",
        resource_id=uuid4(),
        outcome=AuditOutcome.SUCCESS,
        metadata_={},
        occurred_at=now - timedelta(minutes=1),
    )

    await repository.add(older_log)
    await repository.add(newer_log)

    results = await repository.list_for_tenant(
        tenant_id=tenant_id,
    )

    relevant_results = [
        audit_log for audit_log in results if audit_log.id in {older_log.id, newer_log.id}
    ]

    assert [audit_log.id for audit_log in relevant_results] == [
        newer_log.id,
        older_log.id,
    ]
