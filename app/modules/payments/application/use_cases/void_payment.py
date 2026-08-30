from uuid import UUID

from app.modules.audit.application.contracts import AuditRecord
from app.modules.audit.application.use_cases.record_audit_log import (
    RecordAuditLogUseCase,
)
from app.modules.audit.domain.enums import AuditActorType, AuditOutcome
from app.modules.payments.application.ports.unit_of_work import (
    PaymentsUnitOfWork,
)
from app.modules.payments.domain.enums import PaymentStatus
from app.modules.payments.domain.exceptions import (
    InvalidPaymentStateTransitionError,
    PaymentNotFoundError,
)
from app.modules.payments.infrastructure.models.payment import Payment


class VoidPaymentUseCase:
    def __init__(self, unit_of_work: PaymentsUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        *,
        tenant_id: UUID,
        payment_id: UUID,
        actor_id: UUID,
    ) -> Payment:
        async with self._unit_of_work:
            payment = await self._unit_of_work.payments.get_by_id_for_update(
                tenant_id=tenant_id,
                payment_id=payment_id,
            )

            if payment is None:
                raise PaymentNotFoundError

            if payment.status != PaymentStatus.DRAFT:
                raise InvalidPaymentStateTransitionError

            payment.status = PaymentStatus.VOID

            audit = RecordAuditLogUseCase(
                audit_logs=self._unit_of_work.audit_logs,
            )

            await audit.execute(
                AuditRecord(
                    tenant_id=tenant_id,
                    actor_type=AuditActorType.USER,
                    actor_id=actor_id,
                    action="payment.voided",
                    resource_type="payment",
                    resource_id=payment.id,
                    outcome=AuditOutcome.SUCCESS,
                    metadata={
                        "payment_number": payment.payment_number,
                        "amount": str(payment.amount),
                        "currency": payment.currency,
                    },
                )
            )

            await self._unit_of_work.commit()
            await self._unit_of_work.payments.refresh(payment)

            return payment
