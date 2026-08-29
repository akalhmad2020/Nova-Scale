from app.core.database import SessionFactory
from app.modules.payments.application.use_cases.add_payment_allocation import (
    AddPaymentAllocationUseCase,
)
from app.modules.payments.application.use_cases.create_payment import (
    CreatePaymentUseCase,
)
from app.modules.payments.application.use_cases.get_payment import (
    GetPaymentUseCase,
)
from app.modules.payments.application.use_cases.list_payments import (
    ListPaymentsUseCase,
)
from app.modules.payments.application.use_cases.post_payment import (
    PostPaymentUseCase,
)
from app.modules.payments.application.use_cases.remove_payment_allocation import (
    RemovePaymentAllocationUseCase,
)
from app.modules.payments.application.use_cases.void_payment import (
    VoidPaymentUseCase,
)
from app.modules.payments.infrastructure.unit_of_work import (
    SQLAlchemyPaymentsUnitOfWork,
)


def get_create_payment_use_case() -> CreatePaymentUseCase:
    return CreatePaymentUseCase(
        unit_of_work=SQLAlchemyPaymentsUnitOfWork(SessionFactory),
    )


def get_get_payment_use_case() -> GetPaymentUseCase:
    return GetPaymentUseCase(
        unit_of_work=SQLAlchemyPaymentsUnitOfWork(SessionFactory),
    )


def get_list_payments_use_case() -> ListPaymentsUseCase:
    return ListPaymentsUseCase(
        unit_of_work=SQLAlchemyPaymentsUnitOfWork(SessionFactory),
    )


def get_add_payment_allocation_use_case() -> AddPaymentAllocationUseCase:
    return AddPaymentAllocationUseCase(
        unit_of_work=SQLAlchemyPaymentsUnitOfWork(SessionFactory),
    )


def get_remove_payment_allocation_use_case() -> RemovePaymentAllocationUseCase:
    return RemovePaymentAllocationUseCase(
        unit_of_work=SQLAlchemyPaymentsUnitOfWork(SessionFactory),
    )


def get_post_payment_use_case() -> PostPaymentUseCase:
    return PostPaymentUseCase(
        unit_of_work=SQLAlchemyPaymentsUnitOfWork(SessionFactory),
    )


def get_void_payment_use_case() -> VoidPaymentUseCase:
    return VoidPaymentUseCase(
        unit_of_work=SQLAlchemyPaymentsUnitOfWork(SessionFactory),
    )
