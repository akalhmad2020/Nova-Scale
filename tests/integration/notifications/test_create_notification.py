import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.modules.notifications.application.use_cases.create_notification import (
    CreateNotificationUseCase,
)
from app.modules.notifications.domain.enums import NotificationChannel
from app.modules.notifications.infrastructure.models.notification import (
    Notification,
)
from app.modules.notifications.infrastructure.repositories.sqlalchemy import (
    SQLAlchemyNotificationRepository,
)
from app.modules.notifications.infrastructure.unit_of_work import (
    SQLAlchemyNotificationUnitOfWork,
)

pytestmark = pytest.mark.integration


class BarrierNotificationRepository(SQLAlchemyNotificationRepository):
    def __init__(
        self,
        session: AsyncSession,
        *,
        barrier: asyncio.Barrier,
    ) -> None:
        super().__init__(session)
        self._barrier = barrier
        self._idempotency_lookup_count = 0

    async def get_by_idempotency_key(
        self,
        *,
        tenant_id: UUID,
        idempotency_key: str,
    ) -> Notification | None:
        result = await super().get_by_idempotency_key(
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
        )

        self._idempotency_lookup_count += 1

        if self._idempotency_lookup_count == 1:
            await self._barrier.wait()

        return result


def make_unit_of_work(
    session: AsyncSession,
    *,
    barrier: asyncio.Barrier,
) -> SQLAlchemyNotificationUnitOfWork:
    unit_of_work = SQLAlchemyNotificationUnitOfWork(session)

    unit_of_work.notifications = BarrierNotificationRepository(
        session,
        barrier=barrier,
    )

    return unit_of_work


async def test_same_idempotency_key_returns_same_notification(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    tenant_id = uuid4()
    idempotency_key = f"invoice-issued-{uuid4()}"

    barrier = asyncio.Barrier(2)

    async with (
        session_factory() as first_session,
        session_factory() as second_session,
    ):
        first_use_case = CreateNotificationUseCase(
            make_unit_of_work(
                first_session,
                barrier=barrier,
            )
        )

        second_use_case = CreateNotificationUseCase(
            make_unit_of_work(
                second_session,
                barrier=barrier,
            )
        )

        first_result, second_result = await asyncio.gather(
            first_use_case.execute(
                tenant_id=tenant_id,
                event_type="invoice.issued",
                recipient="billing@example.com",
                channel=NotificationChannel.EMAIL,
                subject="Invoice issued",
                body="Your invoice has been issued.",
                idempotency_key=idempotency_key,
            ),
            second_use_case.execute(
                tenant_id=tenant_id,
                event_type="invoice.issued",
                recipient="billing@example.com",
                channel=NotificationChannel.EMAIL,
                subject="Invoice issued",
                body="Your invoice has been issued.",
                idempotency_key=idempotency_key,
            ),
        )

    assert first_result.id == second_result.id

    async with session_factory() as verification_session:
        statement = (
            select(
                func.count(Notification.id),
            )
            .select_from(Notification)
            .where(
                Notification.tenant_id == tenant_id,
                Notification.idempotency_key == idempotency_key,
            )
        )

        result = await verification_session.execute(statement)
        count = result.scalar_one()

        assert count == 1


async def test_same_idempotency_key_is_isolated_by_tenant(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    first_tenant_id = uuid4()
    second_tenant_id = uuid4()
    idempotency_key = f"shared-key-{uuid4()}"

    async with (
        session_factory() as first_session,
        session_factory() as second_session,
    ):
        first_use_case = CreateNotificationUseCase(SQLAlchemyNotificationUnitOfWork(first_session))

        second_use_case = CreateNotificationUseCase(
            SQLAlchemyNotificationUnitOfWork(second_session)
        )

        first_result, second_result = await asyncio.gather(
            first_use_case.execute(
                tenant_id=first_tenant_id,
                event_type="invoice.issued",
                recipient="first@example.com",
                channel=NotificationChannel.EMAIL,
                subject="Invoice issued",
                body="First tenant notification.",
                idempotency_key=idempotency_key,
            ),
            second_use_case.execute(
                tenant_id=second_tenant_id,
                event_type="invoice.issued",
                recipient="second@example.com",
                channel=NotificationChannel.EMAIL,
                subject="Invoice issued",
                body="Second tenant notification.",
                idempotency_key=idempotency_key,
            ),
        )

    assert first_result.id != second_result.id
    assert first_result.tenant_id == first_tenant_id
    assert second_result.tenant_id == second_tenant_id

    async with session_factory() as verification_session:
        statement = select(Notification).where(
            Notification.idempotency_key == idempotency_key,
        )

        result = await verification_session.execute(statement)
        notifications = result.scalars().all()

        assert len(notifications) == 2
        assert {notification.tenant_id for notification in notifications} == {
            first_tenant_id,
            second_tenant_id,
        }
