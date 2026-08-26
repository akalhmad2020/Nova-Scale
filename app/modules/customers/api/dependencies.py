from app.core.database import SessionFactory
from app.modules.customers.application.use_cases.create_customer import (
    CreateCustomer,
)
from app.modules.customers.application.use_cases.delete_customer import (
    DeleteCustomer,
)
from app.modules.customers.application.use_cases.get_customer import (
    GetCustomer,
)
from app.modules.customers.application.use_cases.list_customers import (
    ListCustomers,
)
from app.modules.customers.application.use_cases.update_customer import (
    UpdateCustomer,
)
from app.modules.customers.infrastructure.unit_of_work import (
    SQLAlchemyUnitOfWork,
)


def get_delete_customer_use_case() -> DeleteCustomer:
    return DeleteCustomer(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_update_customer_use_case() -> UpdateCustomer:
    return UpdateCustomer(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_create_customer_use_case() -> CreateCustomer:
    return CreateCustomer(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_list_customers_use_case() -> ListCustomers:
    return ListCustomers(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_customer_use_case() -> GetCustomer:
    return GetCustomer(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )
